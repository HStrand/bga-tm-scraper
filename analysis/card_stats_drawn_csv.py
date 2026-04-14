#!/usr/bin/env python3
"""Same as card_stats_drawn.py but reads CSV — for benchmarking."""

import time
from pathlib import Path
import pandas as pd

data_dir = Path(__file__).parent / "db_dump"

t0 = time.perf_counter()
gamecards = pd.read_csv(
    data_dir / "gamecards.csv",
    usecols=["TableId", "PlayerId", "Card", "DrawnGen"],
    low_memory=False,
)
gameplayers = pd.read_csv(
    data_dir / "gameplayers_canonical.csv",
    usecols=["TableId", "PlayerId", "Position", "Elo", "EloChange"],
    low_memory=False,
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
print(f"Rows: {len(result)}")
