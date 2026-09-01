#!/usr/bin/env python3
"""Recalibrate the GEN-1 value of a science tag from the current model constants.

Each instrument solves for `sci` (gen-1-visible science-tag value). Observed =
hand-strength-controlled (all-not-played) gen-1 deltas.
"""
import math

EPM = 0.14
EARTH = 1.0
SPACE = 1.0
MCPROD = 5.7
PLANT = 9.0
VP = 1.5
ONESHOT_DRAW = 0.0   # gen-1-visible value of a single drawn card (deferred ~ 0)

est = []  # (label, sci, seSci, note)

# 1) Inventors' Guild - Business Network : continuous card-draw CANCELS.
#    pred_IG - pred_BN = EPM*(sci - EARTH + MCPROD - (12 - 7))
oIG, sIG = 0.466, 0.103
oBN, sBN = 0.097, 0.096
diff = oIG - oBN
sdiff = math.hypot(sIG, sBN)
sci = diff / EPM + EARTH - MCPROD + 5
est.append(("IG - Business Network", sci, sdiff / EPM,
            "draw cancels; only needs Earth, MCprod"))

# 2) Designed Microorganisms: 2 plant prod + sci + microbe(0).  cost 19.
o, s = 0.427, 0.111
sci = o / EPM - (2 * PLANT + 0 - 19)
est.append(("Designed Microorganisms", sci, s / EPM, "needs plant=9"))

# 3) Trans-Neptune Probe: sci + space + 1 VP.  cost 9.
o, s = -0.178, 0.264
sci = o / EPM - (SPACE + VP - 9)
est.append(("Trans-Neptune Probe", sci, s / EPM, "needs space, VP; noisy"))

# 4) Lagrange Observatory: sci + space + 1 VP + one-shot draw.  cost 12.
o, s = -0.887, 0.149
sci = o / EPM - (SPACE + VP + ONESHOT_DRAW - 12)
est.append(("Lagrange Observatory", sci, s / EPM, "needs oneshot draw~0"))

print(f"EPM={EPM}, Earth={EARTH}, Space={SPACE}, MCprod={MCPROD}, plant={PLANT}, VP={VP}\n")
print(f"{'Instrument':<26}{'sci':>8}{'+/-SE':>8}  note")
num = den = 0.0
for label, sci, se, note in est:
    w = 1.0 / se ** 2
    num += w * sci
    den += w
    print(f"{label:<26}{sci:>8.2f}{se:>8.2f}  {note}")

print(f"\nInverse-variance combined GEN-1 science value = {num/den:.2f} "
      f"+/- {den**-0.5:.2f} MC")

# Excluded: Search For Life (-0.835) -- trap-filler (negative selection F),
# and its non-tag 'effect' value is unknown, so unusable as a clean instrument.
