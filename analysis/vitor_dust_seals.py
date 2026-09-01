#!/usr/bin/env python3
"""Avg EloChange for Vitor playing a given card in gen 1 (standard filters)."""

import sys
from pathlib import Path

import duckdb

card = sys.argv[1] if len(sys.argv) > 1 else "Dust Seals"
gen = int(sys.argv[2]) if len(sys.argv) > 2 else 1

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
vitor_players AS (
    SELECT DISTINCT gps.TableId, gps.PlayerId
    FROM '{gameplayerstats}' gps
    JOIN filtered_tables ft USING (TableId)
    WHERE gps.Corporation = 'Vitor'
),
vitor_elo AS (
    SELECT vp.TableId, vp.PlayerId, gp.EloChange,
           EXISTS (
               SELECT 1 FROM '{gamecards}' gc
               WHERE gc.TableId = vp.TableId
                 AND gc.PlayerId = vp.PlayerId
                 AND gc.Card = '{card}'
                 AND gc.PlayedGen = {gen}
           ) AS PlayedGen1
    FROM vitor_players vp
    JOIN '{gameplayers}' gp
      ON gp.TableId = vp.TableId AND gp.PlayerId = vp.PlayerId
    WHERE gp.EloChange IS NOT NULL
)
SELECT
    CASE WHEN PlayedGen1 THEN 'Vitor, {card} played gen {gen}'
         ELSE 'Vitor, no gen-{gen} {card}' END AS Cohort,
    COUNT(*) AS Games,
    AVG(CAST(EloChange AS DOUBLE)) AS AvgEloChange,
    STDDEV(CAST(EloChange AS DOUBLE)) / SQRT(COUNT(*)) AS StdErr
FROM vitor_elo
GROUP BY PlayedGen1

UNION ALL

SELECT 'Vitor, all games', COUNT(*),
       AVG(CAST(EloChange AS DOUBLE)),
       STDDEV(CAST(EloChange AS DOUBLE)) / SQRT(COUNT(*))
FROM vitor_elo
ORDER BY Cohort
"""

print(duckdb.sql(query).df().to_string(index=False))
