#!/usr/bin/env python3
"""Avg EloChange when a card is played in a given gen, any corp (standard filters).

Usage: python card_gen_elo.py "Card Name" [gen]
"""

import sys
from pathlib import Path

import duckdb

card = sys.argv[1]
gen = int(sys.argv[2]) if len(sys.argv) > 2 else 1

here = Path(__file__).parent
data_dir = here / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()

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
    SELECT gp.TableId, gp.PlayerId, gp.EloChange,
           EXISTS (
               SELECT 1 FROM '{gamecards}' gc
               WHERE gc.TableId = gp.TableId AND gc.PlayerId = gp.PlayerId
                 AND gc.Card = '{card}' AND gc.PlayedGen = {gen}
           ) AS PlayedInGen
    FROM '{gameplayers}' gp
    JOIN filtered_tables ft USING (TableId)
    WHERE gp.EloChange IS NOT NULL
)
SELECT
    CASE WHEN PlayedInGen THEN '{card} played gen {gen}'
         ELSE 'Not played gen {gen}' END AS Cohort,
    COUNT(*) AS Games,
    AVG(CAST(EloChange AS DOUBLE)) AS AvgEloChange,
    STDDEV(CAST(EloChange AS DOUBLE)) / SQRT(COUNT(*)) AS StdErr
FROM players
GROUP BY PlayedInGen
ORDER BY Cohort
"""

print(duckdb.sql(query).df().to_string(index=False))
