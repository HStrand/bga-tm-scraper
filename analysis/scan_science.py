#!/usr/bin/env python3
"""Goodness-of-fit scan for the gen-1 science-tag value.

For each trial value X, chi-square = sum_i (X - sci_i)^2 / se_i^2 over the four
science instruments from solve_science.py. Best fit minimizes chi-square.
"""
# (label, sci estimate, SE)  -- from solve_science.py
inst = [
    ("IG - Business Network", 2.94, 1.01),
    ("Designed Microorganisms", 4.05, 0.79),
    ("Trans-Neptune Probe", 5.23, 1.89),
    ("Lagrange Observatory", 3.16, 1.06),
]


def chi2(X):
    return sum((X - s) ** 2 / se ** 2 for _, s, se in inst)


# Inverse-variance best estimate (the chi-square minimizer).
num = sum(s / se ** 2 for _, s, se in inst)
den = sum(1 / se ** 2 for _, s, se in inst)
best = num / den
print(f"Best-fit (chi-square min) = {best:.2f} +/- {den**-0.5:.2f}\n")

print(f"{'trial':>6}{'chi2':>8}{'dChi2':>8}")
for X in [2.6, 3.0, 3.4, 3.6, 3.8, 4.0, 4.4, 5.0]:
    print(f"{X:>6.1f}{chi2(X):>8.3f}{chi2(X)-chi2(best):>8.3f}")

print("\nPer-instrument residual (trial - estimate) in SE units:")
print(f"{'trial':>6}" + "".join(f"{lab.split(' ')[0][:6]:>8}" for lab, _, _ in inst))
for X in [3.6, 4.0]:
    print(f"{X:>6.1f}" + "".join(f"{(X-s)/se:>+8.2f}" for _, s, se in inst))
