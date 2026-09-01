#!/usr/bin/env python3
"""Find card names matching a substring. Usage: python find_card.py <substr>"""
import sys
from pathlib import Path
import duckdb

sub = sys.argv[1]
gc = (Path(__file__).parent / "db_dump" / "gamecards.parquet").as_posix()
q = f"""
SELECT Card, COUNT(*) AS n
FROM '{gc}'
WHERE Card ILIKE '%{sub}%'
GROUP BY Card ORDER BY n DESC
"""
print(duckdb.sql(q).df().to_string(index=False))
