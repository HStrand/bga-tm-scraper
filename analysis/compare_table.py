#!/usr/bin/env python3
"""Full predicted-vs-observed table. Predictions from model_predict.py constants;
observed = hand-strength-controlled (all-not-played) gen-1 deltas from hand_table.py.
Sorted by residual within tiers.
"""
import importlib.util
from pathlib import Path

# Pull predictions straight from model_predict (re-exec to capture its CARDS/C).
mp_path = Path(__file__).parent / "model_predict.py"
spec = importlib.util.spec_from_file_location("model_predict", mp_path)
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)
pred = {c: mp.C["elo_per_mc"] * (mp.value(comp) - (base + 3))
        for c, (base, comp, _) in mp.CARDS.items()}

# Observed hand-controlled deltas (all-not-played, +HandStrength) and SEs.
obs = {
    "Power Plant": (-0.072, .099), "Geothermal Power": (0.079, .109),
    "Giant Space Mirror": (0.045, .123), "Peroxide Power": (0.048, .136),
    "Nuclear Power": (0.212, .174), "Micro-Mills": (-0.544, .150),
    "Import of Advanced GHG": (-0.423, .103), "Soletta": (-0.190, .128),
    "Archaebacteria": (-0.059, .090), "Adapted Lichen": (-0.846, .121),
    "Designed Microorganisms": (0.427, .111), "Lichen": (0.360, .262),
    "Search For Life": (-0.835, .136), "Trans-Neptune Probe": (-0.178, .264),
    "Lagrange Observatory": (-0.887, .149), "Inventors' Guild": (0.466, .103),
    "Business Network": (0.097, .096), "Building Industries": (0.441, .096),
    "Industrial Microbes": (0.358, .085), "Mine": (0.567, .073),
    "Asteroid Mining Consortium": (1.785, .141), "Io Mining Industries": (0.845, .106),
    "Asteroid Mining": (0.226, .097), "Titanium Mine": (0.630, .076),
    "Vesta Shipyard": (-0.038, .088), "Phobos Space Haven": (-1.256, .133),
    "Protected Habitats": (-0.852, .116), "Pets": (-0.955, .113),
    "Rover Construction": (-1.021, .097), "Space Station": (-0.588, .118),
    "Arctic Algae": (0.003, .089), "Viral Enhancers": (-0.500, .145),
    "Sponsors": (0.440, .076), "Acquired Company": (0.713, .078),
    "Immigration Shuttles": (-0.021, .128), "Hackers": (0.994, .111),
}

rows = []
for c in mp.CARDS:
    o, se = obs[c]
    p = pred[c]
    resid = o - p
    rows.append((c, p, o, se, resid, abs(resid) / se))

rows.sort(key=lambda r: abs(r[4]))
print(f"{'Card':<28}{'pred':>8}{'obs':>8}{'SE':>7}{'resid':>8}{'|t|':>6}")
for c, p, o, se, resid, t in rows:
    print(f"{c:<28}{p:>+8.3f}{o:>+8.3f}{se:>7.3f}{resid:>+8.3f}{t:>6.1f}")

import statistics
res = [r[4] for r in rows]
print(f"\nn={len(res)}  mean resid={statistics.mean(res):+.3f}  "
      f"rms resid={(sum(x*x for x in res)/len(res))**0.5:.3f}  "
      f"within 1 SE: {sum(1 for r in rows if r[5] <= 1)}/{len(rows)}")
