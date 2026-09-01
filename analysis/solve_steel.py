#!/usr/bin/env python3
"""Re-derive gen-1 steel-PROD value from Mine, Industrial Microbes, Building
Industries. Observed = hand-strength-controlled (all-not-played) deltas.

obs = EPM * (steel*S + energy*E - cost).
Two views: (1) per-card implied S with energy fixed at 7, inverse-variance
combined; (2) joint weighted least-squares fit of (S, E) from all three.
"""
import numpy as np

EPM = 0.14
ENERGY = 7.0

# (label, obs, se, cost, steel_count, energy_count)
cards = [
    ("Mine",                0.567, 0.073,  7, 1,  0),
    ("Industrial Microbes", 0.358, 0.085, 15, 1,  1),
    ("Building Industries", 0.441, 0.096,  9, 2, -1),
]

print(f"EPM={EPM}, energy fixed at {ENERGY}\n")
print(f"{'Card':<22}{'impliedS':>10}{'+/-SE':>8}")
num = den = 0.0
for label, o, s, cost, sc, ec in cards:
    S = (o / EPM - ec * ENERGY + cost) / sc
    seS = s / (EPM * sc)
    w = 1 / seS ** 2
    num += w * S
    den += w
    print(f"{label:<22}{S:>10.2f}{seS:>8.2f}")
print(f"{'COMBINED (E=7)':<22}{num/den:>10.2f}{den**-0.5:>8.2f}")

# Joint WLS fit of [S, E]: rows = cards, design = [steel_count, energy_count],
# RHS = obs/EPM + cost, weights = 1/(se/EPM)^2.
A, b, w = [], [], []
for label, o, s, cost, sc, ec in cards:
    A.append([sc, ec]); b.append(o / EPM + cost); w.append((EPM / s) ** 2)
A = np.array(A); b = np.array(b); W = np.diag(w)
cov = np.linalg.inv(A.T @ W @ A)
x = cov @ A.T @ W @ b
se = np.sqrt(np.diag(cov))
print(f"\nJoint fit (free energy):  steel = {x[0]:.2f} +/- {se[0]:.2f}, "
      f"energy = {x[1]:.2f} +/- {se[1]:.2f}")
