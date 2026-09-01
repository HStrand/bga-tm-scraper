#!/usr/bin/env python3
"""Export card predicted/observed gen-1 deltas to CSV.

Columns: Card, ActualCost (printed cost + 3 MC card buy = what you pay),
ModelCost (model's fair value = sum of assigned component values),
PredictedDelta (model), ObservedDelta (hand-strength-controlled, all-not-played).
"""
import csv
import importlib.util
from pathlib import Path

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location("model_predict", here / "model_predict.py")
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)

obs = {
    "Power Plant": -0.072, "Geothermal Power": 0.079, "Giant Space Mirror": 0.045,
    "Peroxide Power": 0.048, "Nuclear Power": 0.212, "Micro-Mills": -0.544,
    "Import of Advanced GHG": -0.423, "Soletta": -0.190, "Archaebacteria": -0.059,
    "Adapted Lichen": -0.846, "Designed Microorganisms": 0.427, "Lichen": 0.360,
    "Search For Life": -0.835, "Trans-Neptune Probe": -0.178,
    "Lagrange Observatory": -0.887, "Inventors' Guild": 0.466,
    "Business Network": 0.097, "Building Industries": 0.441,
    "Industrial Microbes": 0.358, "Mine": 0.567,
    "Asteroid Mining Consortium": 1.785, "Io Mining Industries": 0.845,
    "Asteroid Mining": 0.226, "Titanium Mine": 0.630, "Vesta Shipyard": -0.038,
    "Phobos Space Haven": -1.256, "Protected Habitats": -0.852, "Pets": -0.955,
    "Rover Construction": -1.021, "Space Station": -0.588,
    "Viral Enhancers": -0.500, "Sponsors": 0.440, "Acquired Company": 0.713,
    "Immigration Shuttles": -0.021, "Hackers": 0.994,
}

out = here / "card_deltas.csv"
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Card", "ActualCost", "ModelCost", "PredictedDelta", "ObservedDelta"])
    for card, (base, comp, _) in mp.CARDS.items():
        actual_cost = base + 3            # what you pay (printed + card buy)
        model_cost = mp.value(comp)       # model's fair value (sum of components)
        pred = mp.C["elo_per_mc"] * (model_cost - actual_cost)
        w.writerow([card, actual_cost, round(model_cost, 1),
                    round(pred, 3), round(obs[card], 3)])

print(f"Wrote {out} ({len(mp.CARDS)} cards)")
