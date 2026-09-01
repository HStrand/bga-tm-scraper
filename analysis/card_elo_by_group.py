#!/usr/bin/env python3
"""Scatter: avg EloChange when played vs play count, colored by handpicked group."""

import time
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd

here = Path(__file__).parent
data_dir = here / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
handpicked_csv = here / "handpicked_card_clusters.csv"
out_csv = here / "card_elo_by_group.csv"
out_png = here / "card_elo_by_group.png"

groups = pd.read_csv(handpicked_csv, sep=";", encoding="utf-8-sig")
groups.columns = [c.strip() for c in groups.columns]
print(f"Handpicked groups: {len(groups)} cards across {groups['Group'].nunique()} groups")

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
print(f"DuckDB pull: {time.perf_counter() - t0:.2f}s - {len(stats)} cards with stats")

merged = groups.merge(stats, on="Card", how="left")
missing = merged[merged["GameCount"].isna()]["Card"].tolist()
if missing:
    print(f"\n{len(missing)} cards in handpicked CSV had no stats (excluded from plot):")
    for c in missing:
        print(f"  - {c}")
merged = merged.dropna(subset=["GameCount"]).copy()
merged["GameCount"] = merged["GameCount"].astype(int)
merged = merged.sort_values(["Group", "AvgEloChange"], ascending=[True, False])
merged.to_csv(out_csv, index=False)
print(f"\nWrote {out_csv} ({len(merged)} cards)")

groups_sorted = sorted(merged["Group"].unique())
cmap = plt.get_cmap("tab10")
n_panels = len(groups_sorted)
ncols = 3
nrows = (n_panels + ncols - 1) // ncols
fig, axes = plt.subplots(nrows, ncols, figsize=(22, 14), sharex=True, sharey=True)
axes = axes.flatten()

xmin = merged["GameCount"].min()
xmax = merged["GameCount"].max()
ymin = merged["AvgEloChange"].min()
ymax = merged["AvgEloChange"].max()
ypad = (ymax - ymin) * 0.05

for i, grp in enumerate(groups_sorted):
    ax = axes[i]
    others = merged[merged["Group"] != grp]
    sub = merged[merged["Group"] == grp]
    ax.scatter(others["GameCount"], others["AvgEloChange"], s=14,
               color="lightgrey", alpha=0.45, edgecolor="none", zorder=1)
    ax.scatter(sub["GameCount"], sub["AvgEloChange"], s=46, color=cmap(i),
               alpha=0.9, edgecolor="white", linewidth=0.5, zorder=3)
    ax.axhline(0, color="grey", linewidth=0.7, alpha=0.5, zorder=2)
    ax.set_title(f"{grp}  (n={len(sub)},  mean={sub['AvgEloChange'].mean():.2f})")
    ax.grid(True, alpha=0.25)
    for _, row in sub.iterrows():
        ax.annotate(row["Card"], (row["GameCount"], row["AvgEloChange"]),
                    fontsize=6, alpha=0.85, xytext=(3, 2), textcoords="offset points")

for j in range(n_panels, len(axes)):
    axes[j].set_visible(False)

for ax in axes[-ncols:]:
    ax.set_xlabel("Game count")
for ax in axes[::ncols]:
    ax.set_ylabel("Avg EloChange when played")

xpad = (xmax - xmin) * 0.03
axes[0].set_xlim(xmin - xpad, xmax + xpad)
axes[0].set_ylim(ymin - ypad, ymax + ypad)

fig.suptitle("Avg EloChange when played vs popularity, by handpicked group", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig(out_png, dpi=140)
print(f"Wrote {out_png}")
