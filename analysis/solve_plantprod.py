#!/usr/bin/env python3
"""Exact best-fit for the gen-1 plant-PRODUCTION value, current constants.

Clean instruments only. Archaebacteria is fully confound-free (microbe tag~0,
no requirement, no science) -> the independent anchor. Designed Microorganisms
also works but uses science=3.6, which was itself partly derived from DM, so it
is mildly circular -- shown separately and in the combine.
Excluded: Adapted Lichen (trap-filler F), Lichen (-24C requirement +selection).
"""
import math

EPM = 0.14
SCIENCE = 3.6
MICROBE = 0.0

# (label, obs, se, cost, plant_count, other_value, note)
inst = [
    ("Archaebacteria",          -0.059, 0.090,  9, 1, MICROBE,           "fully clean"),
    ("Designed Microorganisms",  0.427, 0.111, 19, 2, SCIENCE + MICROBE, "uses science=3.6 (circular)"),
]

print(f"EPM={EPM}, science={SCIENCE}, microbe={MICROBE}\n")
print(f"{'Instrument':<26}{'impliedP':>10}{'+/-SE':>8}  note")
num = den = 0.0
for label, o, s, cost, pc, other, note in inst:
    P = (o / EPM - other + cost) / pc
    seP = s / (EPM * pc)
    w = 1 / seP ** 2
    num += w * P
    den += w
    print(f"{label:<26}{P:>10.2f}{seP:>8.2f}  {note}")

print(f"\nArchaebacteria alone (independent) = {(-0.059/EPM - MICROBE + 9):.2f} "
      f"+/- {0.090/EPM:.2f}")
print(f"Combined (both)                    = {num/den:.2f} +/- {den**-0.5:.2f}")
