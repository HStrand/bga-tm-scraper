#!/usr/bin/env python3
"""Compare sink depth/timing for players who play a given energy card in gen 1
vs the rest (standard filters): avg # of sink cards played, % with a sink by
gen 3, and elo delta split by early sink.

Usage: python energy_sink_depth.py "Card Name" [gen] [sink_by_gen]
"""

import sys
from pathlib import Path

import duckdb

card = sys.argv[1]
gen = int(sys.argv[2]) if len(sys.argv) > 2 else 1
sink_by = int(sys.argv[3]) if len(sys.argv) > 3 else gen + 2

here = Path(__file__).parent
data_dir = here / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()

sinks = [
    "Steelworks", "Ironworks", "Ore Processor", "Water Splitting Plant",
    "Power Infrastructure", "Physics Complex", "Electro Catapult",
    "Open City", "Urbanized Area", "Immigrant City", "Cupola City",
    "Domed Crater", "Noctis City", "Underground City", "Capital",
    "Corporate Stronghold", "AI Central", "Magnetic Field Dome",
    "Magnetic Field Generators",
]
sink_list = ", ".join(f"'{s}'" for s in sinks)

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
           ) AS PlayedCard,
           (
               SELECT COUNT(DISTINCT gc.Card) FROM '{gamecards}' gc
               WHERE gc.TableId = gp.TableId AND gc.PlayerId = gp.PlayerId
                 AND gc.Card IN ({sink_list}) AND gc.PlayedGen IS NOT NULL
           ) AS SinkCount,
           EXISTS (
               SELECT 1 FROM '{gamecards}' gc
               WHERE gc.TableId = gp.TableId AND gc.PlayerId = gp.PlayerId
                 AND gc.Card IN ({sink_list}) AND gc.PlayedGen <= {sink_by}
           ) AS EarlySink
    FROM '{gameplayers}' gp
    JOIN filtered_tables ft USING (TableId)
    WHERE gp.EloChange IS NOT NULL
)
SELECT
    CASE WHEN PlayedCard THEN '{card} gen {gen}' ELSE 'Rest' END AS Cohort,
    COUNT(*) AS Games,
    AVG(CAST(SinkCount AS DOUBLE)) AS AvgSinks,
    AVG(CASE WHEN EarlySink THEN 1.0 ELSE 0.0 END) AS PctEarlySink
FROM players
GROUP BY 1
ORDER BY Cohort;

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
           ) AS PlayedCard,
           EXISTS (
               SELECT 1 FROM '{gamecards}' gc
               WHERE gc.TableId = gp.TableId AND gc.PlayerId = gp.PlayerId
                 AND gc.Card IN ({sink_list}) AND gc.PlayedGen <= {sink_by}
           ) AS EarlySink
    FROM '{gameplayers}' gp
    JOIN filtered_tables ft USING (TableId)
    WHERE gp.EloChange IS NOT NULL
)
SELECT
    CASE
        WHEN PlayedCard AND EarlySink THEN '{card} gen {gen} + sink by gen {sink_by}'
        WHEN PlayedCard THEN '{card} gen {gen}, no early sink'
        WHEN EarlySink THEN 'No {card}, sink by gen {sink_by}'
        ELSE 'Neither'
    END AS Cohort,
    COUNT(*) AS Games,
    AVG(CAST(EloChange AS DOUBLE)) AS AvgEloChange,
    STDDEV(CAST(EloChange AS DOUBLE)) / SQRT(COUNT(*)) AS StdErr
FROM players
GROUP BY 1
ORDER BY Cohort
"""

con = duckdb.connect()
parts = query.split(";")
for part in parts:
    if part.strip():
        print(con.sql(part).df().to_string(index=False))
        print()
