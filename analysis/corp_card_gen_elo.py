#!/usr/bin/env python3
"""Avg EloChange for a corp playing a given card in a given gen (standard filters).

Usage: python corp_card_gen_elo.py "Corporation" "Card Name" [gen]
"""

import sys
from pathlib import Path

import duckdb

corp = sys.argv[1]
card = sys.argv[2]
gen = int(sys.argv[3]) if len(sys.argv) > 3 else 1

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
corp_players AS (
    SELECT DISTINCT gps.TableId, gps.PlayerId
    FROM '{gameplayerstats}' gps
    JOIN filtered_tables ft USING (TableId)
    WHERE gps.Corporation = '{corp}'
),
corp_elo AS (
    SELECT cp.TableId, cp.PlayerId, gp.EloChange,
           EXISTS (
               SELECT 1 FROM '{gamecards}' gc
               WHERE gc.TableId = cp.TableId
                 AND gc.PlayerId = cp.PlayerId
                 AND gc.Card = '{card}'
                 AND gc.PlayedGen = {gen}
           ) AS PlayedInGen
    FROM corp_players cp
    JOIN '{gameplayers}' gp
      ON gp.TableId = cp.TableId AND gp.PlayerId = cp.PlayerId
    WHERE gp.EloChange IS NOT NULL
)
SELECT
    CASE WHEN PlayedInGen THEN '{corp}, {card} played gen {gen}'
         ELSE '{corp}, not played gen {gen}' END AS Cohort,
    COUNT(*) AS Games,
    AVG(CAST(EloChange AS DOUBLE)) AS AvgEloChange,
    STDDEV(CAST(EloChange AS DOUBLE)) / SQRT(COUNT(*)) AS StdErr
FROM corp_elo
GROUP BY PlayedInGen
ORDER BY Cohort
"""

print(duckdb.sql(query).df().to_string(index=False))
