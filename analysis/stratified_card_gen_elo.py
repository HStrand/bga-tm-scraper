#!/usr/bin/env python3
"""Corp-stratified elo delta for playing a card in a given gen (standard filters).

Within each corporation, compares played-in-gen vs not-played, then averages
the per-corp deltas weighted by the played-cohort size. Removes corp-mix
(Simpson's paradox) distortion from the pooled estimate.

Usage: python stratified_card_gen_elo.py "Card Name" [gen]
"""

import math
import sys
from pathlib import Path

import duckdb

card = sys.argv[1]
gen = int(sys.argv[2]) if len(sys.argv) > 2 else 1
card_sql = card.replace("'", "''")

here = Path(__file__).parent
data_dir = here / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (data_dir / "gameplayerstats.parquet").as_posix()

query = f"""
WITH filtered_tables AS (
    SELECT DISTINCT g.TableId
    FROM '{games}' g
    JOIN '{gamestats}' gs USING (TableId)
    WHERE g.ColoniesOn = FALSE
      AND g.PreludeOn = TRUE
      AND g.CorporateEraOn = TRUE
      AND g.GameMode <> 'Friendly mode'
      AND g.Map <> 'Amazonis Planitia'
      AND gs.PlayerCount = 2
),
players AS (
    SELECT gp.TableId, gp.PlayerId, gp.EloChange, gps.Corporation,
           EXISTS (
               SELECT 1 FROM '{gamecards}' gc
               WHERE gc.TableId = gp.TableId AND gc.PlayerId = gp.PlayerId
                 AND gc.Card = '{card_sql}' AND gc.PlayedGen = {gen}
           ) AS PlayedInGen
    FROM '{gameplayers}' gp
    JOIN filtered_tables ft USING (TableId)
    JOIN (
        SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gameplayerstats}'
    ) gps ON gps.TableId = gp.TableId AND gps.PlayerId = gp.PlayerId
    WHERE gp.EloChange IS NOT NULL
)
SELECT Corporation,
       COUNT(*) FILTER (WHERE PlayedInGen) AS PlayedGames,
       AVG(CAST(EloChange AS DOUBLE)) FILTER (WHERE PlayedInGen) AS PlayedAvg,
       STDDEV(CAST(EloChange AS DOUBLE)) FILTER (WHERE PlayedInGen)
           / SQRT(COUNT(*) FILTER (WHERE PlayedInGen)) AS PlayedSE,
       COUNT(*) FILTER (WHERE NOT PlayedInGen) AS ControlGames,
       AVG(CAST(EloChange AS DOUBLE)) FILTER (WHERE NOT PlayedInGen) AS ControlAvg,
       STDDEV(CAST(EloChange AS DOUBLE)) FILTER (WHERE NOT PlayedInGen)
           / SQRT(COUNT(*) FILTER (WHERE NOT PlayedInGen)) AS ControlSE
FROM players
GROUP BY Corporation
HAVING COUNT(*) FILTER (WHERE PlayedInGen) >= 20
ORDER BY PlayedGames DESC
"""

df = duckdb.sql(query).df()
df["Delta"] = df["PlayedAvg"] - df["ControlAvg"]
df["DeltaSE"] = (df["PlayedSE"] ** 2 + df["ControlSE"] ** 2) ** 0.5

w = df["PlayedGames"]
total = float((w * df["Delta"]).sum() / w.sum())
total_se = math.sqrt(float((w**2 * df["DeltaSE"] ** 2).sum())) / float(w.sum())

cols = ["Corporation", "PlayedGames", "PlayedAvg", "ControlAvg", "Delta", "DeltaSE"]
print(df[cols].to_string(index=False))
print(f"\n{card} gen {gen}: stratified delta = {total:+.3f} +/- {total_se:.3f} "
      f"({int(w.sum())} played games across {len(df)} corps)")
