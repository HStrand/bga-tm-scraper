#!/usr/bin/env python3
"""Corporation values in MC: tangible content vs observed, implied ability value.

ObservedValue = BASELINE + ObservedDelta / EPM   (delta from corp_hand.py,
                all-not-kept + full-hand control, raw EloChange)
Tangible      = starting MC + priced production/resources/tags/cards/tiles
                (corp_specs.py, model constants)
Ability       = ObservedValue - Tangible  = MC value of the corp's special
                ability (discount / action / triggered effect) over a 2p game.

BASELINE = value of the average displaced corporation (solve_corp_baseline.py,
anchored on Helion / Inventrix / Point Luna).

Run corp_hand.py first. Usage: python corp_table.py [--baseline B]
"""
import sys
from pathlib import Path

import pandas as pd

from corp_specs import CORPS, EPM, contents, tangible

BASELINE = 68.0
argv = sys.argv[1:]
if "--baseline" in argv:
    BASELINE = float(argv[argv.index("--baseline") + 1])

here = Path(__file__).parent
d = pd.read_csv(here / "corp_hand_deltas.csv").set_index("Corporation")

print(f"Baseline = {BASELINE} MC,  EPM = {EPM}   (ObsVal = baseline + delta/EPM)\n")
print(f"{'Corporation':<26}{'ObsD':>8}{'ObsVal':>8}{'Tang':>7}{'Ability':>9}{'+/-':>6}  "
      f"contents  |  ability")
rows = []
for name in CORPS:
    delta, se = d.loc[name, "all_delta"], d.loc[name, "all_se"]
    ov = BASELINE + delta / EPM
    tg = tangible(name)
    rows.append((name, delta, ov, tg, ov - tg, se / EPM))
rows.sort(key=lambda r: r[2], reverse=True)
for name, delta, ov, tg, ab, ab_se in rows:
    print(f"{name:<26}{delta:>+8.3f}{ov:>8.1f}{tg:>7.1f}{ab:>+9.1f}{ab_se:>6.1f}  "
          f"{contents(name)}  |  {CORPS[name][2]}")

vals = [r[2] for r in rows]
print(f"\nObserved corp values: {min(vals):.1f} .. {max(vals):.1f} MC "
      f"(spread {max(vals) - min(vals):.1f}); unweighted mean {sum(vals) / len(vals):.1f}")
