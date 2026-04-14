#!/usr/bin/env python3
"""
Find the 2-player game where the winner played the fewest cards.

Uses PlayedGen column in gamecards to determine which cards were played.
"""

import pandas as pd
from pathlib import Path

data_dir = Path(__file__).parent / "db_dump"

# Load data
gamestats = pd.read_parquet(data_dir / "gamestats.parquet")
gamecards = pd.read_parquet(data_dir / "gamecards.parquet")
gameplayers = pd.read_parquet(data_dir / "gameplayers.parquet")
gameplayerstats = pd.read_parquet(data_dir / "gameplayerstats.parquet")
games = pd.read_parquet(data_dir / "games.parquet")

# Filter to 2-player, non-conceded games with draft, preludes, no beginner corps
games_2p = gamestats[(gamestats["PlayerCount"] == 2) & (gamestats["Conceded"] == False)][["TableId", "Winner"]].copy()
valid_tables = games[(games["BeginnersCorporationsOn"] == False) & (games["DraftOn"] == True) & (games["PreludeOn"] == True)]["TableId"].unique()
games_2p = games_2p[games_2p["TableId"].isin(valid_tables)]
games_2p["Winner"] = games_2p["Winner"].astype("Int64")

# Count played cards per player per game (PlayedGen not null = card was played)
played = gamecards[gamecards["PlayedGen"].notna()].groupby(["TableId", "PlayerId"]).size().reset_index(name="CardsPlayed")

# Join to get only winners' card counts in 2p games
winner_cards = played.merge(games_2p, on="TableId")
winner_cards = winner_cards[winner_cards["PlayerId"] == winner_cards["Winner"]]

# Find the game with the fewest cards played by the winner
min_row = winner_cards.loc[winner_cards["CardsPlayed"].idxmin()]
table_id = min_row["TableId"]
winner_id = min_row["Winner"]
cards_played = min_row["CardsPlayed"]

print(f"=== 2-Player Game Where Winner Played the Fewest Cards ===\n")
print(f"TableId: {table_id}")
print(f"Cards played by winner: {cards_played}\n")

# Get player names and scores
players = gameplayers[gameplayers["TableId"] == table_id][["PlayerId", "PlayerName", "Position"]]
stats = gameplayerstats[gameplayerstats["TableId"] == table_id][["PlayerId", "Corporation", "FinalScore"]]
player_info = players.merge(stats, on="PlayerId")

for _, p in player_info.sort_values("Position").iterrows():
    role = "WINNER" if p["PlayerId"] == winner_id else "LOSER"
    print(f"[{role}] {p['PlayerName']} — {p['Corporation']} — Score: {p['FinalScore']}")

# Show the cards the winner played
winner_played = gamecards[(gamecards["TableId"] == table_id) & (gamecards["PlayerId"] == winner_id) & (gamecards["PlayedGen"].notna())]
print(f"\nCards played by winner:")
for _, c in winner_played.sort_values("PlayedGen").iterrows():
    print(f"  Gen {int(c['PlayedGen'])}: {c['Card']}")

# Game stats
game = gamestats[gamestats["TableId"] == table_id].iloc[0]
print(f"\nGenerations: {game['Generations']}")
print(f"Duration: {game['DurationMinutes']} minutes")
