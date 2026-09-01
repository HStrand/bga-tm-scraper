#!/usr/bin/env python3
"""Solve for MC-prod value M from the cleanest MC-prod cards.

Model: obs = EPM * (count*M + tags + VP*vp - cost)
  =>   count*M = obs/EPM - tags - VP*vp + cost  =: y
Per card: M_i = y_i / count_i,  SE(M_i) = SE_obs / (EPM*count_i).
Combined: inverse-variance weighted mean across cards.

Observed = hand-strength-controlled (all-not-played) gen-1 deltas.
"""
EPM = 0.14
VP = 1.5
EARTH = 1.0
SPACE = 1.0

# name: (obs, se, cost, mc_prod_count, tags_value, vp_count, note)
cards = {
    "Sponsors":             (+0.440, 0.076,  9, 2, EARTH,         0, "Earth; no VP (clean)"),
    "Acquired Company":     (+0.713, 0.078, 13, 3, EARTH,         0, "Earth; no VP (clean)"),
    "Immigration Shuttles": (-0.021, 0.128, 34, 5, EARTH + SPACE, 2, "Earth+Space; ~2 scored VP"),
}

print(f"EPM={EPM}, VP={VP}, Earth={EARTH}, Space={SPACE}\n")
print(f"{'Card':<20}{'obs':>8}{'count':>6}{'impliedM':>10}{'+/-SE':>8}  note")
num = den = 0.0
for n, (obs, se, cost, cnt, tags, vp, note) in cards.items():
    y = obs / EPM - tags - VP * vp + cost
    M = y / cnt
    seM = se / (EPM * cnt)
    w = 1.0 / seM ** 2
    num += w * M
    den += w
    print(f"{n:<20}{obs:>+8.3f}{cnt:>6}{M:>10.3f}{seM:>8.3f}  {note}")

M_hat = num / den
se_hat = den ** -0.5
print(f"\nInverse-variance combined MC-prod value M = {M_hat:.3f} +/- {se_hat:.3f}")
