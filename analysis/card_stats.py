#!/usr/bin/env python3
"""Card play stats from parquet — equivalent to the Azure SQL query."""

import time
from pathlib import Path
import pandas as pd

data_dir = Path(__file__).parent / "db_dump"

t0 = time.perf_counter()
gamecards = pd.read_parquet(
    data_dir / "gamecards.parquet",
    columns=["TableId", "PlayerId", "Card", "PlayedGen"],
)
gameplayers = pd.read_parquet(
    data_dir / "gameplayers_canonical.parquet",
    columns=["TableId", "PlayerId", "Position", "Elo", "EloChange"],
)
t_load = time.perf_counter() - t0

t0 = time.perf_counter()
played = gamecards[gamecards["PlayedGen"].notna()]
merged = played.merge(gameplayers, on=["TableId", "PlayerId"], how="inner")
merged["Win"] = (merged["Position"] == 1).astype(float)

result = merged.groupby("Card").agg(
    TimesPlayed=("Card", "size"),
    WinRate=("Win", "mean"),
    AvgElo=("Elo", "mean"),
    AvgEloChange=("EloChange", "mean"),
).reset_index()

result["WinRate"] = result["WinRate"].round(3)
result["AvgElo"] = result["AvgElo"].round(2)
result["AvgEloChange"] = result["AvgEloChange"].round(2)
result = result.sort_values("TimesPlayed", ascending=False)
t_query = time.perf_counter() - t0

print(f"Load time:  {t_load:.2f}s")
print(f"Query time: {t_query:.2f}s")
print(f"Total:      {t_load + t_query:.2f}s")
print(f"Rows: {len(result)}\n")
print(result.to_string(index=False))
