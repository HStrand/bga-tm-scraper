#!/usr/bin/env python3
"""Card draw stats via DuckDB — filters on DrawnGen instead of PlayedGen."""

import time
from pathlib import Path
import duckdb

data_dir = Path(__file__).parent / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()

query = f"""
SELECT
    gc.Card,
    COUNT(*) AS TimesDrawn,
    ROUND(AVG(CASE WHEN gp.Position = 1 THEN 1.0 ELSE 0.0 END), 3) AS WinRate,
    ROUND(AVG(CAST(gp.Elo AS DOUBLE)), 2) AS AvgElo,
    ROUND(AVG(CAST(gp.EloChange AS DOUBLE)), 2) AS AvgEloChange
FROM '{gamecards}' gc
JOIN '{gameplayers}' gp
  ON gp.TableId  = gc.TableId
 AND gp.PlayerId = gc.PlayerId
WHERE gc.DrawnGen IS NOT NULL
  AND NOT starts_with(LOWER(gc.Card), 'a card')
  AND NOT starts_with(LOWER(gc.Card), 'card ')
  AND NOT starts_with(LOWER(gc.Card), 'card_main')
  AND NOT starts_with(LOWER(gc.Card), 'card_prelude')
  AND LOWER(gc.Card) NOT LIKE '%(no undo beyond this point)%'
  AND gc.Card NOT IN ('Power plant', 'Greenery', 'City', 'Sell patents', 'Aquifer')
GROUP BY gc.Card
ORDER BY AvgEloChange DESC
"""

t0 = time.perf_counter()
df = duckdb.sql(query).df()
elapsed = time.perf_counter() - t0

print(f"DuckDB total: {elapsed:.2f}s")
print(f"Rows: {len(df)}\n")
print(df.head(100).to_string(index=False))
