#!/usr/bin/env python3
"""Avg EloChange: Dust Seals gen 2 given Earth Catapult played gen 1-2, any corp (standard filters)."""

from pathlib import Path

import duckdb

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
                 AND gc.Card = 'Earth Catapult' AND gc.PlayedGen IN (1, 2)
           ) AS EcGen12,
           EXISTS (
               SELECT 1 FROM '{gamecards}' gc
               WHERE gc.TableId = gp.TableId AND gc.PlayerId = gp.PlayerId
                 AND gc.Card = 'Dust Seals' AND gc.PlayedGen = 2
           ) AS DsGen2
    FROM '{gameplayers}' gp
    JOIN filtered_tables ft USING (TableId)
    WHERE gp.EloChange IS NOT NULL
)
SELECT
    CASE
        WHEN EcGen12 AND DsGen2 THEN 'EC gen 1-2 + Dust Seals gen 2'
        WHEN EcGen12 THEN 'EC gen 1-2, no gen-2 Dust Seals'
        WHEN DsGen2 THEN 'Dust Seals gen 2, no EC gen 1-2'
        ELSE 'Neither'
    END AS Cohort,
    COUNT(*) AS Games,
    AVG(CAST(EloChange AS DOUBLE)) AS AvgEloChange,
    STDDEV(CAST(EloChange AS DOUBLE)) / SQRT(COUNT(*)) AS StdErr
FROM players
GROUP BY 1
ORDER BY Cohort
"""

print(duckdb.sql(query).df().to_string(index=False))
