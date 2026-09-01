#!/usr/bin/env python3
"""Check per-(TableId, PlayerId) duplication in tables used by vitor_dust_seals.py."""

from pathlib import Path

import duckdb

data_dir = Path(__file__).parent / "db_dump"

for name, keys in [
    ("gameplayers_canonical", "TableId, PlayerId"),
    ("gameplayerstats", "TableId, PlayerId"),
    ("gamecards", "TableId, PlayerId, Card"),
]:
    p = (data_dir / f"{name}.parquet").as_posix()
    total = duckdb.sql(f"SELECT COUNT(*) FROM '{p}'").df().iloc[0, 0]
    dup = duckdb.sql(f"""
        SELECT COUNT(*) FROM (
            SELECT {keys} FROM '{p}' GROUP BY {keys} HAVING COUNT(*) > 1
        )
    """).df().iloc[0, 0]
    print(f"{name}: {total} rows, {dup} keys ({keys}) with >1 row")
