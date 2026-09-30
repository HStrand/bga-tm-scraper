"""Tangible starting content of each corporation, priced at the model constants.

Shared by solve_corp_baseline.py and corp_table.py. TANGIBLE = the parts of the
corp that the linear MC-pricing model already prices (starting MC, production,
resources, tags, cards, tiles). Everything else -- discounts, actions, triggered
effects -- is the ABILITY, which is what the corp analysis backs out:

    ObservedValue = BASELINE + delta / EPM
    Ability       = ObservedValue - TANGIBLE

Constants follow reference values from the prelude/project work: MC prod 5.7,
steel prod 10, ti prod 14, energy prod 7, heat prod 4.5, plant prod 9; one-time
resources steel 2.0, ti 2.5, plant 1.5, heat 1.7; tags Earth/Space/Plant/Jovian 1,
Science 3.6, Building 0 (only value is steel payability -- irrelevant on a corp),
Power 0; card draw 4 (at setup); city tile 9.
"""
EPM = 0.14

C = dict(mc_prod=5.7, steel_prod=10.0, ti_prod=14.0, energy_prod=7.0,
         heat_prod=4.5, plant_prod=9.0,
         steel=2.0, ti=2.5, plant=1.5, heat=1.7,
         earth=1.0, space=1.0, plant_tag=1.0, jovian=1.0, science=3.6,
         building=0.0, power=0.0, card=4.0, city=9.0, mc=1.0,
         heat_prod_as_mc=5.7)   # Helion: heat spendable as MC => floor = MC prod

# name: (start_mc, {component: count}, ability description)
CORPS = {
    "CrediCor":          (57, {},                                        "+4 MC after each >=20 MC card / standard project"),
    "Ecoline":           (36, {"plant_prod": 2, "plant": 3, "plant_tag": 1},   "greenery costs 7 plants (not 8). INTERACTION: under Ecoline plant prod ~10 (x8/7) and plants ~1.7, so of the ~11 ability ~2.6 is its own production being worth more and ~8 is the effect on everything else; split not uniquely identifiable"),
    "Helion":            (42, {"heat_prod_as_mc": 3, "space": 1},          "heat spendable as MC: heat prod counted at the MC-prod floor (5.7) in tangible; ability = flexibility premium only (~2-3 MC; Helion is a baseline anchor, assumed 1.0)"),
    "Mining Guild":      (30, {"steel": 5, "steel_prod": 1, "building": 1},   "+1 steel prod per steel/ti placement bonus"),
    "Interplanetary Cinematics": (30, {"steel": 20, "building": 1},           "+2 MC per event played. NOT SEPARABLE: 20 steel is heavily bulk-discounted (~1.5/steel => ~30, not 40) so the rebate is really ~8-12 MC (4-6 events); needs an event count to pin down"),
    "Inventrix":         (45, {"card": 3, "science": 1},                 "global requirements +/-2 steps"),
    "PhoboLog":          (23, {"ti": 10, "space": 1},                      "titanium worth +1 MC (10 ti -> +10 face; ti prod too)"),
    "Tharsis Republic":  (40, {"city": 1, "building": 1, "mc_prod": 1, "mc": 3}, "+1 MC prod per city (anyone) and +3 MC per own city, IN-GAME (the setup city's own triggers are tangible)"),
    "ThorGate":          (48, {"energy_prod": 1, "power": 1},              "power cards & power-plant SP cost 3 less"),
    "United Nations Mars Initiative": (40, {"earth": 1},                   "action: 3 MC -> +1 TR (if TR raised this gen)"),
    "Teractor":          (60, {"earth": 1},                                "Earth cards cost 3 less (~6 MC = ~2 Earth cards). Earth Office (same effect, 1+3 MC) reads ~8.9 as a gen-1 card, but that is selection-inflated (played when Earth targets are in hand); cash discount at 60 MC unlikely (Loan fits at 1:1)"),
    "Saturn Systems":    (42, {"ti_prod": 1, "jovian": 1, "mc_prod": 1},    "+1 MC prod per Jovian tag played IN-GAME by anyone (setup self-trigger is tangible)"),
    "Cheung Shing Mars": (44, {"mc_prod": 3, "building": 1},                  "building cards cost 2 less"),
    "Point Luna":        (38, {"ti_prod": 1, "earth": 1, "space": 1, "card": 1},       "draw a card per Earth tag played IN-GAME (setup self-draw is tangible)"),
    "Robinson Industries": (47, {},                                      "action: 4 MC -> +1 step of your lowest production"),
    "Valley Trust":      (37, {"science": 1},                            "play 1 extra prelude chosen from 3 (E[best of 3 measured preludes] = 26.4 MC) + science cards cost 2 less (remainder ~3.3 => ~1.6 science cards)"),
    "Vitor":             (45, {"earth": 1},                                "fund an award free; +3 MC per card with non-negative VP"),
}


def tangible(name):
    start, comp, _ = CORPS[name]
    return start + sum(C[k] * n for k, n in comp.items())


def contents(name):
    start, comp, _ = CORPS[name]
    parts = [f"{start} MC"] + [f"{n} {k}" for k, n in comp.items()]
    return ", ".join(parts)
