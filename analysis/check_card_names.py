#!/usr/bin/env python3
"""Verify card name spellings against gamecards.parquet."""

from pathlib import Path

import duckdb

here = Path(__file__).parent
gamecards = (here / "db_dump" / "gamecards.parquet").as_posix()

candidates = [
    "Steelworks", "Ironworks", "Ore Processor", "Water Splitting Plant",
    "Power Infrastructure", "Physics Complex", "Electro Catapult",
    "Open City", "Urbanized Area", "Immigrant City", "Cupola City",
    "Domed Crater", "Noctis City", "Underground City", "Capital",
    "Corporate Stronghold", "AI Central", "Magnetic Field Dome",
    "Magnetic Field Generators",
]

in_list = ", ".join(f"'{c}'" for c in candidates)
query = f"""
SELECT Card, COUNT(*) AS Rows
FROM '{gamecards}'
WHERE Card IN ({in_list})
GROUP BY Card
ORDER BY Card
"""
found = duckdb.sql(query).df()
print(found.to_string(index=False))
missing = set(candidates) - set(found["Card"])
print("\nMissing:", sorted(missing) if missing else "none")
