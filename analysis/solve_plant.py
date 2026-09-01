#!/usr/bin/env python3
"""Solve each plant-prod card for its implied plant-prod value P.

obs = EPM * (plant_count*P + plant_tag + sci_gen1 - cost)   (microbe tag ~ 0)
Observed = hand-controlled (all-not-played) gen-1 deltas.
"""
EPM = 0.14
# name: (obs, cost, plant_count, plant_tag, sci_gen1, note)
cards = {
    "Adapted Lichen":     (-0.846, 12, 1, 1, 0.0, "plant tag; NO requirement"),
    "Archaebacteria":     (-0.059,  9, 1, 0, 0.0, "microbe~0; cold req (+sel)"),
    "Designed Microorg.": (+0.427, 19, 2, 0, 2.6, "sci_gen1=2.6; +microbe~0"),
    "Lichen":             (+0.360, 10, 1, 1, 0.0, "-24C req: strong +sel"),
}
print(f"{'Card':<20}{'obs':>8}{'cost':>6}{'#P':>4}{'impliedP':>10}  note")
for n, (obs, cost, pc, pt, sci, note) in cards.items():
    P = ((obs / EPM) + cost - pt - sci) / pc
    print(f"{n:<20}{obs:>+8.3f}{cost:>6}{pc:>4}{P:>10.2f}  {note}")
