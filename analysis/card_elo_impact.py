#!/usr/bin/env python3
"""
Rank cards by average EloChange when kept in starting hand.

Joins games, gameplayers, gamestats, and startinghandcards to compute the
average Elo gained/lost per card (kept only), in 2-player non-friendly games
with Colonies off, Draft on, and Prelude on.
"""

import pandas as pd

# ── Load data ─────────────────────────────────────────────────────────────

games = pd.read_csv("db_dump/games.csv", encoding="utf-8-sig")
gp = pd.read_csv("db_dump/gameplayers.csv", encoding="utf-8-sig")
gs = pd.read_csv("db_dump/gamestats.csv", encoding="utf-8-sig")
shc = pd.read_csv("db_dump/startinghandcards.csv", encoding="utf-8-sig")

# ── Filter games ──────────────────────────────────────────────────────────

games = games[
    (games["GameMode"] != "Friendly mode")
    & (games["ColoniesOn"] == 0)
    & (games["DraftOn"] == 1)
    & (games["PreludeOn"] == 1)
]

# Deduplicate games: one perspective per TableId (latest IndexedAt)
games = games.sort_values(["IndexedAt", "Id"], ascending=[False, False])
games = games.drop_duplicates(subset="TableId", keep="first")

# 2-player only via gamestats
gs_2p = gs[gs["PlayerCount"] == 2][["TableId"]]
games = games.merge(gs_2p, on="TableId")

# ── Deduplicate gameplayers to match chosen game snapshot ─────────────────

# Keep only gameplayer rows whose (TableId, GameId) matches the chosen game
gp = gp.merge(games[["TableId", "Id"]].rename(columns={"Id": "GameId"}), on=["TableId", "GameId"])

gp["EloChange"] = pd.to_numeric(gp["EloChange"], errors="coerce")
gp["CalibratedEloChange"] = pd.to_numeric(gp["CalibratedEloChange"], errors="coerce")

# ── Kept cards ────────────────────────────────────────────────────────────

kept = shc[shc["Kept"] == 1][["TableId", "PlayerId", "Card"]].drop_duplicates()

# ── Join and aggregate ────────────────────────────────────────────────────

merged = kept.merge(
    gp[["TableId", "PlayerId", "EloChange", "CalibratedEloChange"]],
    on=["TableId", "PlayerId"],
)

result = (
    merged.groupby("Card")
    .agg(
        GameCount=("EloChange", "count"),
        AvgEloChange=("EloChange", "mean"),
        AvgCalibratedEloChange=("CalibratedEloChange", "mean"),
    )
    .reset_index()
)

result = result[result["GameCount"] >= 100]
result = result.sort_values("AvgCalibratedEloChange", ascending=False)
result["AvgEloChange"] = result["AvgEloChange"].round(2)
result["AvgCalibratedEloChange"] = result["AvgCalibratedEloChange"].round(2)

# ── Output ────────────────────────────────────────────────────────────────

out_path = "starting_hand_stats/card_elo_impact.csv"
result.to_csv(out_path, index=False)

print(f"Cards with >= 100 games: {len(result)}")
print(f"Total player-card observations: {len(merged):,}")
print(f"Saved to {out_path}")
