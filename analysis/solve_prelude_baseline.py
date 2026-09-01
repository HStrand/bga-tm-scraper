#!/usr/bin/env python3
"""Back out the displaced-prelude baseline from each measured prelude.

delta_X = 0.14 * (V_nominal_X - V_baseline)  =>  V_baseline = V_nominal - delta/EPM.
If the model's content-pricing is right and there's one baseline, all preludes
should imply the same V_baseline. Observed = all-not-kept, full-hand control.
"""
EPM = 0.14
# name: (V_nominal, delta, delta_SE)
p = {
    "Donation":          (21.0, -0.589, 0.089),
    "Metals Company":    (29.7,  0.760, 0.056),
    "Allied Banks":      (26.8,  0.407, 0.105),
    "Business Empire":   (29.2,  0.826, 0.054),
    "Mining Operations": (28.0,  0.629, 0.060),
    "Loan":              (18.6, -0.741, 0.140),
}

print(f"{'Prelude':<20}{'Vnom':>7}{'delta':>8}{'impliedBase':>13}{'+/-SE':>8}")
rows = []
for name, (V, d, se) in p.items():
    base = V - d / EPM
    seb = se / EPM
    rows.append((name, base, seb))
    print(f"{name:<20}{V:>7.1f}{d:>+8.3f}{base:>13.2f}{seb:>8.2f}")


def wmean(items):
    num = sum(b / se ** 2 for _, b, se in items)
    den = sum(1 / se ** 2 for _, b, se in items)
    return num / den, den ** -0.5


all_b = wmean(rows)
no_don = wmean([r for r in rows if r[0] != "Donation"])
print(f"\nWeighted baseline, all 6      = {all_b[0]:.2f} +/- {all_b[1]:.2f}")
print(f"Weighted baseline, excl Donation = {no_don[0]:.2f} +/- {no_don[1]:.2f}")

base = no_don[0]
print(f"\nResiduals at baseline {base:.1f} (obs delta - pred):")
print(f"{'Prelude':<20}{'pred':>8}{'obs':>8}{'resid':>8}")
for name, (V, d, se) in p.items():
    pred = EPM * (V - base)
    print(f"{name:<20}{pred:>+8.3f}{d:>+8.3f}{d-pred:>+8.3f}")
