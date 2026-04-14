#!/usr/bin/env python3
"""Card draw stats from parquet — filters on DrawnGen instead of PlayedGen."""

import time
from pathlib import Path
import pandas as pd

data_dir = Path(__file__).parent / "db_dump"

t0 = time.perf_counter()
gamecards = pd.read_parquet(
    data_dir / "gamecards.parquet",
    columns=["TableId", "PlayerId", "Card", "DrawnGen"],
)
gameplayers = pd.read_parquet(
    data_dir / "gameplayers_canonical.parquet",
    columns=["TableId", "PlayerId", "Position", "Elo", "EloChange"],
)
t_load = time.perf_counter() - t0

t0 = time.perf_counter()
drawn = gamecards[gamecards["DrawnGen"].notna()]
merged = drawn.merge(gameplayers, on=["TableId", "PlayerId"], how="inner")
merged["Win"] = (merged["Position"] == 1).astype(float)

result = merged.groupby("Card").agg(
    TimesDrawn=("Card", "size"),
    WinRate=("Win", "mean"),
    AvgElo=("Elo", "mean"),
    AvgEloChange=("EloChange", "mean"),
).reset_index()

result["WinRate"] = result["WinRate"].round(3)
result["AvgElo"] = result["AvgElo"].round(2)
result["AvgEloChange"] = result["AvgEloChange"].round(2)
result = result.sort_values("TimesDrawn", ascending=False)
t_query = time.perf_counter() - t0

print(f"Load time:  {t_load:.2f}s")
print(f"Query time: {t_query:.2f}s")
print(f"Total:      {t_load + t_query:.2f}s")
print(f"Rows: {len(result)}\n")
print(result.to_string(index=False))
