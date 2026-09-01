#!/usr/bin/env python3
"""Lift in avg EloChange per corporation when playing cards from each handpicked group.

For each (corp, group): avg EloChange across all card-plays of cards in that group,
minus the corp's baseline (avg EloChange across all card-plays). Per-card-play style,
matching analysis/card_elo_by_group.py.
"""

import time
from pathlib import Path

import duckdb
import pandas as pd

here = Path(__file__).parent
data_dir = here / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (data_dir / "gameplayerstats.parquet").as_posix()
handpicked_csv = here / "handpicked_card_clusters.csv"
out_csv = here / "corp_lift_by_group.csv"
out_long_csv = here / "corp_lift_by_group_long.csv"

groups = pd.read_csv(handpicked_csv, sep=";", encoding="utf-8-sig")
groups.columns = [c.strip() for c in groups.columns]
print(f"Handpicked groups: {len(groups)} cards across {groups['Group'].nunique()} groups")

con = duckdb.connect()
con.register("groups_df", groups)

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
plays AS (
    SELECT
        gps.Corporation,
        gc.Card,
        CAST(gp.EloChange AS DOUBLE) AS EloChange
    FROM '{gamecards}' gc
    JOIN filtered_tables ft USING (TableId)
    JOIN '{gameplayers}' gp
      ON gp.TableId = gc.TableId AND gp.PlayerId = gc.PlayerId
    JOIN '{gameplayerstats}' gps
      ON gps.TableId = gc.TableId AND gps.PlayerId = gc.PlayerId
    WHERE gc.PlayedGen IS NOT NULL
      AND gps.Corporation IS NOT NULL
)
SELECT p.Corporation, p.Card, g.Group, p.EloChange
FROM plays p
LEFT JOIN groups_df g ON g.Card = p.Card
"""

t0 = time.perf_counter()
plays = con.sql(query).df()
print(f"DuckDB pull: {time.perf_counter() - t0:.2f}s - {len(plays):,} card-plays")

baseline = (
    plays.groupby("Corporation")
    .agg(BaselineAvg=("EloChange", "mean"), BaselinePlays=("EloChange", "size"))
    .reset_index()
)
print(f"Corporations: {len(baseline)}")

grouped = plays.dropna(subset=["Group"])
per = (
    grouped.groupby(["Corporation", "Group"])
    .agg(GroupAvg=("EloChange", "mean"), GroupPlays=("EloChange", "size"))
    .reset_index()
)

all_groups = sorted(groups["Group"].unique())
all_corps = sorted(baseline["Corporation"].unique())
grid = pd.MultiIndex.from_product([all_corps, all_groups], names=["Corporation", "Group"]).to_frame(index=False)
per = grid.merge(per, on=["Corporation", "Group"], how="left")
per = per.merge(baseline, on="Corporation", how="left")
per["Lift"] = per["GroupAvg"] - per["BaselineAvg"]

per_long = per[["Corporation", "Group", "BaselineAvg", "BaselinePlays",
                "GroupAvg", "GroupPlays", "Lift"]].copy()
per_long = per_long.sort_values(["Corporation", "Lift"], ascending=[True, False])
per_long.to_csv(out_long_csv, index=False)
print(f"Wrote {out_long_csv}")

lift_wide = per.pivot(index="Corporation", columns="Group", values="Lift")
lift_wide = lift_wide[all_groups]
lift_wide.insert(0, "BaselineAvg", baseline.set_index("Corporation")["BaselineAvg"])
lift_wide.insert(1, "BaselinePlays", baseline.set_index("Corporation")["BaselinePlays"])
lift_wide = lift_wide.sort_values("BaselineAvg", ascending=False)
lift_wide.to_csv(out_csv)
print(f"Wrote {out_csv}")

print("\nLift (GroupAvg - BaselineAvg) per corp x group:\n")
disp = lift_wide.copy()
for c in disp.columns:
    if c == "BaselinePlays":
        disp[c] = disp[c].map(lambda v: f"{int(v):>6d}")
    else:
        disp[c] = disp[c].map(lambda v: f"{v:+.2f}" if pd.notna(v) else "  n/a")
print(disp.to_string())

print("\nTop boosters per group (lift, min 100 plays):")
qual = per[per["GroupPlays"] >= 100].copy()
for grp in all_groups:
    sub = qual[qual["Group"] == grp].sort_values("Lift", ascending=False)
    print(f"\n  {grp}:")
    print(f"    Most boosted:  {sub.head(3)[['Corporation','Lift','GroupPlays']].to_string(index=False)}")
    print(f"    Least boosted: {sub.tail(3)[['Corporation','Lift','GroupPlays']].to_string(index=False)}")
