#!/usr/bin/env python3
"""Interactive HTML panel: avg EloChange when played vs popularity, by handpicked group."""

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
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
handpicked_csv = here / "handpicked_card_clusters.csv"
out_html = here / "card_elo_by_group.html"

groups = pd.read_csv(handpicked_csv, sep=";", encoding="utf-8-sig")
groups.columns = [c.strip() for c in groups.columns]

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
)
SELECT
    gc.Card,
    COUNT(*) AS GameCount,
    AVG(CAST(gp.EloChange AS DOUBLE)) AS AvgEloChange
FROM '{gamecards}' gc
JOIN filtered_tables ft USING (TableId)
JOIN '{gameplayers}' gp
  ON gp.TableId = gc.TableId AND gp.PlayerId = gc.PlayerId
WHERE gc.PlayedGen IS NOT NULL
GROUP BY gc.Card
"""

t0 = time.perf_counter()
stats = duckdb.sql(query).df()
print(f"DuckDB pull: {time.perf_counter() - t0:.2f}s")

merged = groups.merge(stats, on="Card", how="inner")
merged["GameCount"] = merged["GameCount"].astype(int)
merged["AvgEloChange"] = merged["AvgEloChange"].round(3)
merged = merged.sort_values(["Group", "AvgEloChange"], ascending=[True, False])

group_means = merged.groupby("Group")["AvgEloChange"].mean().round(2).to_dict()
merged["GroupLabel"] = merged["Group"].map(
    lambda g: f"{g} (n={int((merged['Group'] == g).sum())}, mean={group_means[g]:.2f})"
)

fig = px.scatter(
    merged,
    x="GameCount",
    y="AvgEloChange",
    color="Group",
    facet_col="GroupLabel",
    facet_col_wrap=3,
    hover_data={"Card": True, "GameCount": ":,", "AvgEloChange": ":.3f", "Group": True, "GroupLabel": False},
    text="Card",
    height=820,
    title="Avg EloChange when played vs popularity, by handpicked group",
)

fig.update_traces(
    textposition="top center",
    textfont=dict(size=9),
    marker=dict(size=9, line=dict(width=0.5, color="white")),
)
fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig.add_hline(y=0, line_dash="dot", line_color="grey", opacity=0.5)
fig.update_xaxes(title_text="Game count", matches="x")
fig.update_yaxes(title_text="Avg EloChange when played", matches="y")
fig.update_layout(showlegend=False, hovermode="closest", margin=dict(t=80, l=60, r=20, b=60))

fig.write_html(out_html, include_plotlyjs="cdn", full_html=True)
print(f"Wrote {out_html}  ({len(merged)} cards)")
