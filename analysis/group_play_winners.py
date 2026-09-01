#!/usr/bin/env python3
"""Winners-only: % of each handpicked group's cards the winner plays, by game-ending generation."""

import time
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px

here = Path(__file__).parent
data_dir = here / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
handpicked_csv = here / "handpicked_card_clusters.csv"
out_csv = here / "group_play_winners.csv"
out_html = here / "group_play_winners.html"

GENS = [8, 9, 10, 11, 12]

groups_df = pd.read_csv(handpicked_csv, sep=";", encoding="utf-8-sig")
groups_df.columns = [c.strip() for c in groups_df.columns]
group_sizes = groups_df.groupby("Group").size().to_dict()
print("Group sizes:", group_sizes)

con = duckdb.connect()
con.register("groups_df", groups_df)

gens_list = ", ".join(str(g) for g in GENS)
query = f"""
WITH filtered_tables AS (
    SELECT g.TableId, gs.Generations, CAST(gs.Winner AS BIGINT) AS WinnerId
    FROM '{games}' g
    JOIN '{gamestats}' gs USING (TableId)
    WHERE g.ColoniesOn = FALSE
      AND g.PreludeOn = TRUE
      AND g.CorporateEraOn = TRUE
      AND g.GameMode <> 'Friendly mode'
      AND g.Map <> 'Amazonis Planitia'
      AND gs.PlayerCount = 2
      AND gs.Generations IN ({gens_list})
      AND gs.Winner IS NOT NULL
),
played AS (
    SELECT
        ft.Generations,
        gc.TableId,
        gc.PlayerId,
        gr."Group" AS GroupName,
        COUNT(DISTINCT gc.Card) AS CardsPlayed
    FROM '{gamecards}' gc
    JOIN filtered_tables ft
      ON ft.TableId = gc.TableId
     AND ft.WinnerId = CAST(gc.PlayerId AS BIGINT)
    JOIN groups_df gr ON gr.Card = gc.Card
    WHERE gc.PlayedGen IS NOT NULL
    GROUP BY ft.Generations, gc.TableId, gc.PlayerId, gr."Group"
),
winner_games AS (
    SELECT DISTINCT ft.Generations, ft.TableId, ft.WinnerId AS PlayerId
    FROM '{gamecards}' gc
    JOIN filtered_tables ft
      ON ft.TableId = gc.TableId
     AND ft.WinnerId = CAST(gc.PlayerId AS BIGINT)
    WHERE gc.PlayedGen IS NOT NULL
)
,
totals AS (
    SELECT Generations, SUM(CardsPlayed) AS TotalCardsPlayed
    FROM played
    GROUP BY Generations
),
by_group AS (
    SELECT Generations, GroupName, SUM(CardsPlayed) AS CardsPlayed
    FROM played
    GROUP BY Generations, GroupName
),
winner_game_counts AS (
    SELECT Generations, COUNT(*) AS PlayerGameCount
    FROM winner_games
    GROUP BY Generations
)
SELECT
    bg.Generations,
    bg.GroupName,
    wgc.PlayerGameCount,
    bg.CardsPlayed,
    t.TotalCardsPlayed,
    100.0 * bg.CardsPlayed / t.TotalCardsPlayed AS PctPlayed
FROM by_group bg
JOIN totals t USING (Generations)
JOIN winner_game_counts wgc USING (Generations)
ORDER BY bg.Generations, bg.GroupName
"""

t0 = time.perf_counter()
res = con.sql(query).df()
print(f"DuckDB pull: {time.perf_counter() - t0:.2f}s")

res["GroupSize"] = res["GroupName"].map(group_sizes)
res["PctPlayed"] = res["PctPlayed"].round(2)
res = res.rename(columns={"GroupName": "Group"})

pivot = res.pivot(index="Generations", columns="Group", values="PctPlayed")
pivot["Total"] = pivot.sum(axis=1).round(2)
counts = res.drop_duplicates("Generations").set_index("Generations")["PlayerGameCount"]
pivot.insert(0, "WinnerGames", counts)

print("\n% composition of winner's played cards, by game-ending generation:")
print(pivot.to_string())

res.to_csv(out_csv, index=False)
print(f"\nWrote {out_csv}")

fig = px.line(
    res, x="Generations", y="PctPlayed", color="Group",
    markers=True,
    hover_data={"PlayerGameCount": ":,", "CardsPlayed": ":,", "TotalCardsPlayed": ":,", "GroupSize": True, "PctPlayed": ":.2f"},
    title="Composition of winner's played cards, by game-ending generation",
    labels={"PctPlayed": "% of winner's played cards", "Generations": "Game-ending generation"},
)
fig.update_traces(line=dict(width=2.5), marker=dict(size=9))
fig.update_layout(hovermode="x unified", height=600, margin=dict(t=70, l=60, r=20, b=60))
fig.update_xaxes(tick0=GENS[0], dtick=1)
fig.write_html(out_html, include_plotlyjs="cdn", full_html=True)
print(f"Wrote {out_html}")
