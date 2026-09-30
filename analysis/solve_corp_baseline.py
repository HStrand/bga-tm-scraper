#!/usr/bin/env python3
"""Back out the displaced-corp BASELINE from corps whose ability is priceable.

Corp analog of solve_prelude_baseline.py. Each player keeps 1 of 2 offered corps,
so a corp's hand-controlled delta (corp_hand.py, vs all-not-kept) measures it
against the average corp it displaces:

    delta_X = EPM * (V_X - BASELINE)   =>   BASELINE = V_X - delta_X / EPM

V_X = TANGIBLE (corp_specs.py) + ability. The baseline is NOT identifiable from
deltas alone (kept-weighted mean delta ~ 0 by construction), so it is anchored on
corps whose ability can be priced WITHOUT card-tag metadata:

  Helion      heat spendable as MC: heat prod priced at the MC-prod floor in
              tangible (corp_specs); ability = flexibility only  -> 1.0 +/- 1.5
  Inventrix   requirements +/-2 steps: small option value       -> 2.0 +/- 2.0
  Point Luna  draw per Earth tag IN-GAME (the setup self-draw is tangible):
              4.74 logged draws/game (games with any logged draw; 28% of games
              log none but played as many Earth cards -> a logging gap) at
              ~3.5 MC per in-game card                           -> 16.6 +/- 3.0

Uncertainty per instrument = SE(delta)/EPM combined with the ability assumption.
Also prints the LOWER BOUND on the baseline from "every ability >= 0".

Run corp_hand.py first (reads corp_hand_deltas.csv).
"""
from pathlib import Path

import pandas as pd

from corp_specs import CORPS, EPM, tangible

here = Path(__file__).parent
d = pd.read_csv(here / "corp_hand_deltas.csv").set_index("Corporation")

# name: (assumed ability MC, assumption SE)
ANCHORS = {
    "Helion":     (1.0, 1.5),
    "Inventrix":  (2.0, 2.0),
    "Point Luna": (16.6, 3.0),
}

print(f"{'Corp':<14}{'tangible':>9}{'ability':>9}{'V':>7}{'delta':>8}{'base':>8}{'+/-':>6}")
rows = []
for name, (ab, ab_se) in ANCHORS.items():
    delta, se = d.loc[name, "all_delta"], d.loc[name, "all_se"]
    V = tangible(name) + ab
    base = V - delta / EPM
    base_se = ((se / EPM) ** 2 + ab_se ** 2) ** 0.5
    rows.append((name, base, base_se))
    print(f"{name:<14}{tangible(name):>9.1f}{ab:>9.1f}{V:>7.1f}{delta:>+8.3f}{base:>8.2f}{base_se:>6.2f}")

num = sum(b / s ** 2 for _, b, s in rows)
den = sum(1 / s ** 2 for _, b, s in rows)
B, B_se = num / den, den ** -0.5
print(f"\nWeighted baseline = {B:.2f} +/- {B_se:.2f} MC")

# Lower bound: no corp's ability can be worth less than 0.
lb = []
for name in CORPS:
    if name == "Interplanetary Cinematics":
        continue  # 20-steel tangible is overstated (bulk), would bias the bound up
    lb.append((tangible(name) - d.loc[name, "all_delta"] / EPM, name))
lb.sort(reverse=True)
print("\nLower bound (ability >= 0), top 4:")
for v, n in lb[:4]:
    print(f"  {n:<34}{v:>7.2f}")

print(f"\nSpread of implied ability values at B={B:.1f}: "
      f"{min(B - v for v, _ in lb):+.1f} .. {max(B - v for v, _ in lb):+.1f} MC")
