#!/usr/bin/env python3
"""Predicted vs observed table for all measured preludes.

ModelValue   = sum of prelude contents (MC), current model constants.
PredictedDelta = EPM * (ModelValue - BASELINE).
ObservedDelta  = measured (all-not-kept, full-hand control), raw EloChange.
ObservedValue  = BASELINE + ObservedDelta / EPM.
Residual       = ObservedValue - ModelValue (MC).

BASELINE = displaced/marginal prelude value, ~23.8 MC (6-card consensus,
excluding the Donation outlier). Add a prelude by appending to PRELUDES.
"""
EPM = 0.14
BASELINE = 23.8

# name: (model_value, observed_delta, delta_SE, contents note)
PRELUDES = {
    "Donation":          (21.0, -0.589, 0.089, "21 cash"),
    "Loan":              (18.6, -0.741, 0.140, "30 cash, -2 MCprod"),
    "Allied Banks":      (26.8,  0.407, 0.105, "4 MCprod, 3 cash, Earth"),
    "Business Empire":   (29.2,  0.826, 0.054, "6 MCprod, -6 cash, Earth"),
    "Metals Company":    (29.7,  0.760, 0.056, "1 MC/1 steel/1 ti prod"),
    "Mining Operations": (28.0,  0.629, 0.060, "2 steel prod, 4 steel"),
    "Martian Industries":(23.0, -0.099, 0.067, "1 steel/1 energy prod, 6 cash"),
    "Dome Farming":      (21.4, -0.152, 0.069, "2 MCprod, 1 plant prod, plant tag"),
    "Biosphere Support": (13.3, -1.572, 0.100, "2 plant prod, plant tag, -1 MCprod"),
    "Society Support":   (14.8, -1.238, 0.136, "-1 MCprod, 1 plant/1 energy/1 heat prod"),
    "Power Generation":  (21.0, -0.338, 0.074, "3 energy prod"),
    "Mohole":            (18.6, -0.748, 0.088, "3 heat prod, 3 heat (heat res~1.7)"),
    "Mohole Excavation": (22.4, -0.202, 0.073, "2 heat prod, 1 steel prod, 2 heat"),
    "Supplier":          (22.0, -0.154, 0.070, "2 energy prod, 4 steel"),
    "Galilean Mining":   (24.0, -0.094, 0.063, "2 ti prod, -5 cash, Jovian tag"),
    "Orbital Construction Yard": (25.0, 0.049, 0.062, "1 ti prod, 4 ti@2.5, space"),
    "Biofuels":          (19.0, -0.663, 0.094, "1 plant/1 energy prod, 2 plant (plant res~1.5)"),
    "Supply Drop":       (28.0,  0.307, 0.069, "3 ti + 8 steel + 3 plant (14 resources, bulk)"),
    "Huge Asteroid":     (21.1, -0.348, 0.074, "3 temp TR@7.2 + 1 heat prod bonus, -5 cash"),
    "Metal-Rich Asteroid": (25.2, 0.185, 0.066, "1 temp TR@7.2, 4 steel, 4 ti@2.5"),
    "Smelting Plant":    (24.4,  0.165, 0.081, "2 oxygen TR@7.2, 5 steel (O~7.5)"),
    "Nitrogen Shipment": (21.2, -0.411, 0.108, "1 bare TR@7.2, 1 plant prod, 5 cash (TR~6.9)"),
    "Great Aquifer":     (28.0,  0.565, 0.061, "2 oceans@14 (pure-ocean instrument)"),
    "Polar Industries":  (23.0,  0.264, 0.070, "1 ocean@14, 2 heat prod (over-performs, ocean synergy?)"),
    "Aquifer Turbines":  (25.0,  0.352, 0.062, "1 ocean@14, 2 energy prod, -3 cash (over-performs)"),
    "UNMI Contractor":   (26.6,  0.675, 0.058, "3 bare TR@7.2, Earth, 1 card draw@4 (+2 anomaly)"),
    "Io Research Outpost": (22.6, -0.160, 0.064, "1 ti prod, science, Jovian, 1 card draw@4"),
    "Biolabs":           (24.6,  0.043, 0.069, "1 science, 1 plant prod, 3 cards@4 (draw~3.8)"),
    "Research Network":  (26.7,  0.430, 0.061, "wild tag@9, 1 MCprod, 3 cards@4 (wild~9.2 if draw=4)"),
    "Acquired Space Agency": (25.0, 0.176, 0.060, "6 ti + 2 space-tag cards (ti<->space SYNERGY; components not separable)"),
    "Self-Sufficient Settlement": (20.4, -0.589, 0.065, "1 city@9, 2 MCprod (clean city~8.2)"),
    "Early Settlement":  (18.0, -0.731, 0.073, "1 city@9, 1 plant prod (city~9.6; +plant synergy?)"),
    "Ecology Experts":   (24.5,  0.094, 0.110, "plant tag, 1 plant prod, play-ignore-reqs (E~14.5 SELECTION-conditional)"),
    "Eccentric Sponsor": (25.0, -0.127, 0.195, "play card -25 MC discount (realizes ~23; n=1630, NOISY)"),
    "Experimental Forest": (25.0, 0.188, 0.064, "2 plant-tag cards@4, greenery@17 (greenery~17)"),
}

print(f"Baseline = {BASELINE} MC,  EPM = {EPM}\n")
print(f"{'Prelude':<20}{'ModelVal':>9}{'ObsVal':>8}{'PredD':>8}{'ObsD':>8}"
      f"{'Resid':>8}{'|t|':>6}  contents")
rows = []
for name, (mv, od, se, note) in PRELUDES.items():
    pd_ = EPM * (mv - BASELINE)
    ov = BASELINE + od / EPM
    resid = ov - mv
    t = abs(od - pd_) / se
    rows.append((name, mv, ov, pd_, od, resid, t, note))

for name, mv, ov, pd_, od, resid, t, note in sorted(rows, key=lambda r: r[5]):
    print(f"{name:<20}{mv:>9.1f}{ov:>8.1f}{pd_:>+8.3f}{od:>+8.3f}"
          f"{resid:>+8.1f}{t:>6.1f}  {note}")

res = [r[5] for r in rows]
print(f"\nn={len(res)}  mean resid={sum(res)/len(res):+.2f} MC  "
      f"rms={ (sum(x*x for x in res)/len(res))**0.5:.2f} MC")
