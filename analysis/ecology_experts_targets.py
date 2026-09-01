#!/usr/bin/env python3
"""Performance of Ecology Experts target cards: EE kept from starting hand, target card played Gen 1."""

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
gameplayers = (data_dir / "gameplayers.parquet").as_posix()
shp = (data_dir / "startinghandpreludes.parquet").as_posix()

out_csv = here / "ecology_experts_targets.csv"
out_html = here / "ecology_experts_targets.html"

TARGETS = [
    "Birds", "Kelp Farming", "Farming", "Trees", "Algae",
    "Bushes", "Fish", "Heather", "Lake Marineris", "Livestock",
]

con = duckdb.connect()
con.execute("CREATE TEMP TABLE targets AS SELECT * FROM (VALUES " +
            ", ".join(f"('{c}')" for c in TARGETS) + ") t(Card)")

query = f"""
WITH filtered_tables AS (
    SELECT g.TableId
    FROM '{games}' g
    JOIN '{gamestats}' gs USING (TableId)
    WHERE g.ColoniesOn = FALSE
      AND g.PreludeOn = TRUE
      AND g.CorporateEraOn = TRUE
      AND g.GameMode <> 'Friendly mode'
      AND g.Map <> 'Amazonis Planitia'
      AND gs.PlayerCount = 2
),
ee_kept AS (
    SELECT DISTINCT sp.TableId, sp.PlayerId
    FROM '{shp}' sp
    JOIN filtered_tables ft USING (TableId)
    WHERE sp.Prelude = 'Ecology Experts'
      AND sp.Kept = TRUE
),
target_plays AS (
    SELECT DISTINCT gc.TableId, gc.PlayerId, gc.Card
    FROM '{gamecards}' gc
    JOIN ee_kept k ON k.TableId = gc.TableId AND k.PlayerId = gc.PlayerId
    JOIN targets t ON t.Card = gc.Card
    WHERE gc.PlayedGen = 1
),
joined AS (
    SELECT
        tp.Card,
        tp.TableId,
        tp.PlayerId,
        gp.Position,
        gp.EloChange
    FROM target_plays tp
    JOIN '{gameplayers}' gp
      ON gp.TableId = tp.TableId
     AND gp.PlayerId = tp.PlayerId
     AND gp.PlayerPerspective = tp.PlayerId
)
SELECT
    Card,
    COUNT(*) AS N,
    AVG(CASE WHEN Position = 1 THEN 1.0 ELSE 0.0 END) AS WinRate,
    AVG(CAST(EloChange AS DOUBLE)) AS AvgEloGain
FROM joined
GROUP BY Card
ORDER BY AvgEloGain DESC
"""

t0 = time.perf_counter()
res = con.sql(query).df()
print(f"DuckDB pull: {time.perf_counter() - t0:.2f}s")

print("\nEcology Experts target performance (EE kept + target played Gen 1):")
print(res.to_string(index=False))

res.to_csv(out_csv, index=False)
print(f"\nWrote {out_csv}")

fig = px.bar(
    res, x="Card", y="AvgEloGain",
    hover_data={"N": ":,", "WinRate": ":.3f", "AvgEloGain": ":.3f"},
    title="Ecology Experts Targets — Avg Elo Gain (EE kept, target played Gen 1)",
    labels={"AvgEloGain": "Avg Elo Gain", "Card": "Card"},
)
fig.update_layout(height=600, margin=dict(t=70, l=60, r=20, b=120))
fig.update_xaxes(tickangle=-45)
fig.write_html(out_html, include_plotlyjs="cdn", full_html=True)
print(f"Wrote {out_html}")
