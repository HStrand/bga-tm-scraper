#!/usr/bin/env python3
"""Card play stats via DuckDB against parquet — same query as the Azure SQL one."""

import time
from pathlib import Path
import duckdb

data_dir = Path(__file__).parent / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()

query = f"""
SELECT
    gc.Card,
    COUNT(*) AS TimesPlayed,
    ROUND(AVG(CASE WHEN gp.Position = 1 THEN 1.0 ELSE 0.0 END), 3) AS WinRate,
    ROUND(AVG(CAST(gp.Elo AS DOUBLE)), 2) AS AvgElo,
    ROUND(AVG(CAST(gp.EloChange AS DOUBLE)), 2) AS AvgEloChange
FROM '{gamecards}' gc
JOIN '{gameplayers}' gp
  ON gp.TableId  = gc.TableId
 AND gp.PlayerId = gc.PlayerId
WHERE gc.PlayedGen IS NOT NULL
GROUP BY gc.Card
ORDER BY TimesPlayed DESC
"""

t0 = time.perf_counter()
df = duckdb.sql(query).df()
elapsed = time.perf_counter() - t0

print(f"DuckDB total: {elapsed:.2f}s")
print(f"Rows: {len(df)}\n")
print(df.head(20).to_string(index=False))
