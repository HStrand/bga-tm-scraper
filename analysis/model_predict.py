#!/usr/bin/env python3
"""Predicted gen-1 elo delta for analyzed cards, from the linear MC-pricing model.

pred = ELO_PER_MC * (sum of component values - total cost incl. 3 MC card buy).
Science tag uses the GEN-1-VISIBLE value (2.6), not lifetime (~6), to match gen-1
deltas; science-tag cards therefore under-predict by design (deferred value).
Caveat cards (Jovian setup premium, deferred-effect self-sabotage) are flagged.
Edit specs/constants below to re-fit.
"""

C = dict(
    elo_per_mc=0.14, mc_prod=5.7, steel_prod=10.0, ti_prod=14.0, energy_prod=7.0,
    plant_prod=9.0, heat_prod=4.5, vp=1.5,
    space=1.0, earth=1.0, plant_tag=1.0, science=3.6, microbe=0.0, jovian=1.0,
    draw_cont=11.0, draw_oneshot=0.0,
)

# Each card: (base_cost, {component: count}, note). Total cost = base_cost + 3.
# 'effect' = raw MC value of a special/deferred effect at gen 1.
CARDS = {
    "Power Plant":               (4,  {"energy_prod": 1}, ""),
    "Geothermal Power":          (11, {"energy_prod": 2}, ""),
    "Giant Space Mirror":        (17, {"energy_prod": 3, "space": 1}, ""),
    "Peroxide Power":            (7,  {"energy_prod": 2, "mc_prod": -1}, ""),
    "Nuclear Power":             (10, {"energy_prod": 3, "mc_prod": -2}, ""),
    "Micro-Mills":               (3,  {"heat_prod": 1}, "trap-filler"),
    "Import of Advanced GHG":    (9,  {"heat_prod": 2}, "event, no kept tag"),
    "Soletta":                   (35, {"heat_prod": 7, "space": 1}, ""),
    "Archaebacteria":            (6,  {"plant_prod": 1, "microbe": 1}, "clean: no req, microbe~0"),
    "Adapted Lichen":            (9,  {"plant_prod": 1, "plant_tag": 1}, ""),
    "Designed Microorganisms":   (16, {"plant_prod": 2, "science": 1, "microbe": 1}, "sci deferred"),
    "Lichen":                    (7,  {"plant_prod": 1, "plant_tag": 1}, "req -24C: +selection"),
    "Search For Life":           (3,  {"science": 1}, "sci deferred; effect uncertain"),
    "Trans-Neptune Probe":       (6,  {"science": 1, "space": 1, "vp": 1}, "sci deferred"),
    "Lagrange Observatory":      (9,  {"science": 1, "space": 1, "vp": 1, "draw_oneshot": 1}, "sci+draw deferred"),
    "Inventors' Guild":          (9,  {"science": 1, "draw_cont": 1}, "sci deferred"),
    "Business Network":          (4,  {"earth": 1, "mc_prod": -1, "draw_cont": 1}, ""),
    "Building Industries":       (6,  {"steel_prod": 2, "energy_prod": -1}, ""),
    "Industrial Microbes":       (12, {"steel_prod": 1, "energy_prod": 1}, ""),
    "Mine":                      (4,  {"steel_prod": 1}, ""),
    "Asteroid Mining Consortium":(13, {"ti_prod": 2, "vp": 1, "jovian": 1}, "ti swing (deny+gain)"),
    "Io Mining Industries":      (41, {"ti_prod": 2, "mc_prod": 2, "vp": 4.2, "jovian": 1, "space": 1}, "4.2 scored VP"),
    "Asteroid Mining":           (30, {"ti_prod": 2, "vp": 2, "space": 1, "jovian": 1}, "CAVEAT: Jovian premium"),
    "Titanium Mine":             (7,  {"ti_prod": 1}, ""),
    "Vesta Shipyard":            (15, {"ti_prod": 1, "jovian": 1, "space": 1}, ""),
    "Phobos Space Haven":        (25, {"ti_prod": 1, "vp": 3, "space": 1}, ""),
    "Protected Habitats":        (5,  {"effect": 1.0}, "deferred: effect~1 gen1"),
    "Pets":                      (10, {"earth": 1}, "CAVEAT: 2.6 VP deferred"),
    "Rover Construction":        (8,  {"vp": 1}, "CAVEAT: 2 MC/city deferred"),
    "Space Station":             (10, {"space": 1}, "CAVEAT: space discount deferred"),
    "Viral Enhancers":           (9,  {"science": 1, "microbe": 1}, "CAVEAT: tag-effect deferred"),
    "Sponsors":                  (6,  {"mc_prod": 2, "earth": 1}, ""),
    "Acquired Company":          (10, {"mc_prod": 3, "earth": 1}, "spec: +3 MC prod?"),
    "Immigration Shuttles":      (31, {"mc_prod": 5, "earth": 1, "space": 1, "vp": 2}, "~2 scored VP"),
    "Hackers":                   (3,  {"mc_prod": 2, "energy_prod": -1, "vp": -1,
                                       "denial_mc_prod": 2}, "denial=full 2p swing"),
}


def value(comp):
    v = 0.0
    for k, n in comp.items():
        if k == "effect":
            v += n
        elif k == "denial_mc_prod":
            v += n * C["mc_prod"]   # 2p symmetry: deny opp = +full to you
        elif k == "denial_ti_prod":
            v += n * C["ti_prod"]
        else:
            v += n * C[k]
    return v


print(f"Model: elo/MC={C['elo_per_mc']}, MCprod={C['mc_prod']}, steel={C['steel_prod']}, "
      f"ti={C['ti_prod']}, energy={C['energy_prod']}, plant={C['plant_prod']}, "
      f"heat={C['heat_prod']}, VP={C['vp']}, sci(gen1)={C['science']}, "
      f"draw_cont={C['draw_cont']}, space={C['space']}, earth={C['earth']}\n")
print(f"{'Card':<28}{'cost':>5}{'value':>8}{'net':>8}{'pred':>8}  note")
for card, (base, comp, note) in CARDS.items():
    cost = base + 3
    val = value(comp)
    net = val - cost
    pred = C["elo_per_mc"] * net
    print(f"{card:<28}{cost:>5}{val:>8.1f}{net:>+8.1f}{pred:>+8.3f}  {note}")
