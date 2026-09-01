#!/usr/bin/env python3
"""Corp composition and per-corp elo for players who play a card in a gen
(standard filters).

Usage: python card_gen_corps.py "Card Name" [gen]
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
played AS (
    SELECT gp.TableId, gp.PlayerId, gp.EloChange
    FROM '{gameplayers}' gp
    JOIN filtered_tables ft USING (TableId)
    WHERE gp.EloChange IS NOT NULL
      AND EXISTS (
          SELECT 1 FROM '{gamecards}' gc
          WHERE gc.TableId = gp.TableId AND gc.PlayerId = gp.PlayerId
            AND gc.Card = '{card}' AND gc.PlayedGen = {gen}
      )
)
SELECT gps.Corporation,
       COUNT(*) AS Games,
       COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS PctOfCohort,
       AVG(CAST(p.EloChange AS DOUBLE)) AS AvgEloChange,
       STDDEV(CAST(p.EloChange AS DOUBLE)) / SQRT(COUNT(*)) AS StdErr
FROM played p
JOIN (
    SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gameplayerstats}'
) gps ON gps.TableId = p.TableId AND gps.PlayerId = p.PlayerId
GROUP BY gps.Corporation
ORDER BY Games DESC
"""

print(duckdb.sql(query).df().to_string(index=False))
