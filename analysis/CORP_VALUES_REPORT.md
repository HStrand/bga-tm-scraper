# Terraforming Mars (BGA, 2-player): What is each Corporation worth in MC?

*Companion to the prelude and project-card pricing work. Data: ~313,000 player-games from BGA replays. Analysis date: 2026-09-01.*

## 1. Summary

- Every corporation was converted to a single **MC-equivalent value**, on the same scale used for preludes (~24 MC average) and project cards.
- The **average corporation is worth 68 MC** (±1.2). Corporations range from **56 MC (UNMI) to 74 MC (Point Luna)** — an 18 MC spread, i.e. the best corp gives you roughly one extra strong prelude (a Business Empire) compared with the worst.
- Each corp's value splits into **tangible content** (starting MC, production, resources, tags, cards, tiles — priced with the existing model constants) and its **ability**, whose MC value is the new result of this analysis. Abilities range from ~1 MC (Inventrix's ±2 requirements) to ~30 MC (Valley Trust's extra prelude).
- Top tier (70–74 MC): Point Luna, Cheung Shing Mars, Saturn Systems, Interplanetary Cinematics, Valley Trust, Ecoline, Vitor, CrediCor. Middle (66–69): Mining Guild, Tharsis Republic, Teractor, Robinson Industries. Bottom (56–62): Helion, Inventrix, PhoboLog, ThorGate, UNMI.
- Players' keep rates track value closely (Point Luna kept 77% of the time it is offered, ThorGate 18%, UNMI 19%) — the community has largely priced corps correctly, with a few exceptions noted below.

## 2. Method

### 2.1 Measuring a corp's effect on results
Each player is offered 2 corporations and keeps 1. For each corporation X we regress a player's **raw Elo change** on a "kept X" indicator with controls for the strength of the *entire* offered starting hand (the other offered corp, all 4 offered preludes, all 10 offered project cards — each item valued by its pooled mean Elo change when kept, precomputed by `build_handstrength.py`). Standard errors are heteroskedasticity-robust (HC1). No corporation fixed effects are used, because the corporation is the treatment.

Filters (the standard set): 2 players, Corporate Era on, Prelude on, Colonies off, not Friendly mode, not Amazonis Planitia. This yields exactly 17 corps (12 base game + 5 Prelude), each offered ~36,500 times.

The coefficient ("delta") is the Elo advantage of keeping X versus the average corp it displaces. Deltas run from +0.86 (Point Luna) to −1.65 (UNMI), with SEs of 0.05–0.09.

### 2.2 Converting Elo to MC
As for preludes: `delta = EPM × (V_corp − BASELINE)`, with **EPM = 0.14 Elo per MC** (from the gen-1 project-card work). Hence `V_corp = BASELINE + delta / 0.14`.

The **baseline** (value of the average displaced corporation) cannot be identified from the deltas alone (they average to ~0 by construction), so it is anchored on three corps whose total value can be priced independently:

| Anchor | Why it can be priced | Implied baseline |
|---|---|---|
| Helion | Heat is spendable as MC, so its 3 heat prod has a hard floor of MC-prod value (3 × 5.7); the only unpriced part is a small flexibility premium (assumed 1 ± 1.5 MC) | 67.2 ± 1.6 |
| Inventrix | 3 cards (4 each) + Science tag (3.6) are model-priced; the ±2 requirement ability is small (assumed 2 ± 2 MC; the card Adaptation Technology with the same effect delivers only ~4.7 MC of effect *including* selection bias) | 69.3 ± 2.1 |
| Point Luna | Its ability is logged in the data: 4.74 corp-triggered card draws per game, valued at ~3.5 MC each (in-game draws are worth a bit less than the 4 MC of a setup card) → 16.6 ± 3 MC | 68.5 ± 3.0 |

Inverse-variance weighted: **BASELINE = 68.0 ± 1.2 MC**. Cross-check: requiring that no corp's ability be worth less than zero gives a lower bound of 67.3, just under the estimate. Discount corps (Teractor, Cheung Shing Mars, CrediCor, ThorGate) were deliberately *not* used as anchors because their usage counts would need card-tag metadata the dataset lacks; their ability values are therefore outputs.

### 2.3 Pricing tangible content
Model constants (MC): MC prod 5.7, steel prod 10, titanium prod 14, energy prod 7, heat prod 4.5 (5.7 for Helion), plant prod 9; one-time steel 2.0, titanium 2.5, plant 1.5, heat 1.7; tags Earth/Space/Plant/Jovian 1, Science 3.6, **Building 0 and Power 0** (a Building tag's only value is steel payability, which never applies to a corporation); card draw at setup 4; city tile 9.

Convention: when a corp's effect triggers on itself at setup (Point Luna's own Earth tag draws a card; Saturn Systems' own Jovian tag gives +1 MC prod; Tharsis Republic's setup city gives +3 MC and +1 MC prod), that setup trigger is counted as **tangible**, so "ability" means the *in-game* part of the effect only.

## 3. Results

Value = observed MC-equivalent value; Ability = Value − Tangible. Ability SE ≈ ±0.4–0.7 MC (statistical); the ±1.2 baseline uncertainty shifts *all* values together.

| # | Corporation | Keep % | Delta (Elo) | **Value (MC)** | Tangible | **Ability (MC)** | Ability |
|---|---|---|---|---|---|---|---|
| 1 | Point Luna | 77 | +0.861 | **74.1** | 58.0 | **16.1** | Draw a card per Earth tag played |
| 2 | Cheung Shing Mars | 60 | +0.537 | **71.8** | 61.1 | **10.7** | Building cards cost 2 less |
| 3 | Saturn Systems | 58 | +0.518 | **71.7** | 62.7 | **9.0** | +1 MC prod per Jovian tag (anyone) |
| 4 | Interplanetary Cinematics | 47 | +0.447 | **71.2** | 70.0* | **1.2*** | +2 MC per event |
| 5 | Valley Trust | 70 | +0.322 | **70.3** | 40.6 | **29.7** | Extra prelude (best of 3) + science cards −2 |
| 6 | Ecoline | 58 | +0.324 | **70.3** | 59.5 | **10.8** | Greenery costs 7 plants |
| 7 | Vitor | 63 | +0.273 | **69.9** | 46.0 | **23.9** | Free award; +3 MC per non-negative-VP card |
| 8 | CrediCor | 63 | +0.225 | **69.6** | 57.0 | **12.6** | +4 MC after each ≥20 MC card / standard project |
| 9 | Mining Guild | 52 | +0.084 | **68.6** | 50.0 | **18.6** | +1 steel prod per steel/ti placement bonus |
| 10 | Tharsis Republic | 56 | +0.072 | **68.5** | 57.7 | **10.8** | +1 MC prod per city (anyone), +3 MC per own city |
| 11 | Teractor | 49 | −0.177 | **66.7** | 61.0 | **5.7** | Earth cards cost 3 less |
| 12 | Robinson Industries | 41 | −0.261 | **66.1** | 47.0 | **19.1** | Action: 4 MC → +1 lowest production |
| 13 | Helion | 39 | −0.847 | **61.9** | 60.1 | **1.8** | Heat spendable as MC (flexibility only; floor is in tangible) |
| 14 | Inventrix | 43 | −0.939 | **61.3** | 60.6 | **0.7** | Requirements ±2 |
| 15 | PhoboLog | 34 | −1.002 | **60.8** | 49.0 | **11.8** | Titanium worth +1 MC |
| 16 | ThorGate | 18 | −1.273 | **58.9** | 55.0 | **3.9** | Power cards −3 |
| 17 | UNMI | 19 | −1.653 | **56.2** | 41.0 | **15.2** | Action: 3 MC → +1 TR |

\* IC's split is not identifiable (see §4.4); its total of 71.2 is solid.

Tangible breakdowns (MC): Point Luna 38 + ti prod 14 + Earth 1 + Space 1 + setup card 4 · Cheung Shing Mars 44 + 3 MC prod 17.1 · Saturn Systems 42 + ti prod 14 + Jovian 1 + setup MC prod 5.7 · IC 30 + 20 steel 40 · Valley Trust 37 + Science 3.6 · Ecoline 36 + 2 plant prod 18 + 3 plants 4.5 + Plant tag 1 · Vitor 45 + Earth 1 · CrediCor 57 · Mining Guild 30 + 5 steel 10 + steel prod 10 · Tharsis 40 + city 9 + 3 MC + setup MC prod 5.7 · Teractor 60 + Earth 1 · Robinson 47 · Helion 42 + 3 heat prod at MC floor 17.1 + Space 1 · Inventrix 45 + 3 cards 12 + Science 3.6 · PhoboLog 23 + 10 ti 25 + Space 1 · ThorGate 48 + energy prod 7 · UNMI 40 + Earth 1.

## 4. Corp-by-corp findings

### 4.1 Card draw and trigger abilities
- **Point Luna (74.1, best corp).** The in-game draw effect is worth ~16 MC. With 4.74 logged draws per game that is ~3.4 MC per drawn card, slightly below the 4 MC of a card in the opening hand — later draws have less time to pay off. (28% of Point Luna games log zero corp draws; these players played just as many Earth cards, so it is a logging gap, and the nonzero-game mean is used.)
- **Saturn Systems (71.7).** The in-game Jovian trigger is worth ~9 MC ≈ 1.6 MC-prod steps at setup price, consistent with 2–3 Jovian tags per game (both players') arriving mid-game at a discount.
- **Tharsis Republic (68.5).** In-game triggers ~10.8 MC ≈ 2–3 further cities on the board (mostly the opponent's), each less than 5.7 because they arrive later.
- **Mining Guild (68.6).** The placement-bonus effect is worth ~18.6 MC, ≈ 2–3 extra steel-prod steps over a game — a lot for a corp with only 50 MC of tangible content.

### 4.2 Discount abilities
- **Cheung Shing Mars (71.8):** −2 on building cards ≈ 10.7 MC ≈ 5.3 building cards per game.
- **CrediCor (69.6):** +4 MC rebate ≈ 12.6 MC ≈ 3 qualifying plays.
- **Teractor (66.7):** −3 on Earth cards ≈ 5.7 MC ≈ 2 Earth cards. The project card **Earth Office** (same effect, 1+3 MC) reads ~8.9 MC as a gen-1 card — but that is **selection-inflated**: Earth Office is bought precisely when the hand already holds Earth cards, whereas Teractor is kept regardless. We considered and rejected "cash is worth less at 60 MC": Loan (+30 cash) and CrediCor (57 MC) both fit at cash = 1 MC.
- **ThorGate (58.9):** −3 on power cards ≈ 3.9 MC ≈ 1.3 power cards. It is only kept 18% of the time, so even this is conditional on having power cards in hand.
- **Valley Trust (70.3):** ability 29.7 = **an extra prelude chosen from 3 ≈ 26.4** (measured prelude values: mean 23.2, sd 3.9; expected best-of-3 = 26.4) + science-card discount ≈ 3.3 (~1.6 science cards).

### 4.3 Action abilities
- **Robinson Industries (66.1):** the action is worth ~19 MC, consistent with ~5 uses at a net gain of ~4 each (4 MC buys a steel/ti/energy prod step worth 7–14 when that is your lowest).
- **UNMI (56.2, worst corp):** the 3 MC → TR action is worth ~15 MC (≈ 3–4 uses at ~4.2 net), but the corp is so thin otherwise (40 MC + Earth tag) that it ends 12 MC below average. The 19% keep rate shows players know.
- **Vitor (69.9):** ~24 MC ≈ a free award (8–10 MC) plus ~5 VP cards × 3 MC.

### 4.4 Bundles and interactions (split not uniquely identifiable)
- **Interplanetary Cinematics (71.2).** At face value 20 steel = 40 MC, leaving only 1.2 MC for the event rebate, which is not credible. The real story is a **bulk discount**: 20 steel is ~40 MC of building discount that cannot be spent efficiently in gens 1–3, so the marginal steel idles. Consistent with earlier findings (Supply Drop 14 resources −1.4 MC; Metal-Rich Asteroid 8 resources −0.9), the working split is 20 steel ≈ 30 MC (~1.5/steel) and the rebate ≈ 8–12 MC (4–6 events). An event count from the data would settle it.
- **Ecoline (70.3).** Greenery at 7 plants makes Ecoline's own plant production worth ~10 per step (× 8/7) and its plants ~1.7; of the ~10.8 ability, ~2.6 is the production being worth more and ~8 is the effect on all other plant sources. The two reinforce each other.
- **PhoboLog (60.8).** Ability 11.8 ≈ +1 MC on each of the 10 starting titanium plus the same bonus on titanium produced later, net of a bulk discount on 10 ti.

### 4.5 Small abilities
- **Helion (61.9):** with heat prod priced at the MC-prod floor (5.7), the remaining flexibility premium is ~2–3 MC. Helion's weakness is not its ability but its thin content (60 MC tangible vs a 68 average).
- **Inventrix (61.3):** ±2 requirements ≈ 0–2 MC. Adaptation Technology (12+3 MC, same effect + Science tag + 1 VP) delivers only ~9.8 MC total (gen-1 delta −0.73), i.e. ≈4.7 MC for the effect even with selection bias in its favour — the effect mostly buys tempo, not access, in a 2p game.

## 5. Take-aways for a presentation
1. **Corps are worth ~68 MC on average**, about 2.9 preludes (23.8 each). Corp choice matters about as much as one prelude: best vs worst = 18 MC ≈ 2.5 Elo per game.
2. **Abilities are typically worth 10–20 MC** — comparable to a strong prelude. The biggest are Valley Trust's extra prelude (~30), Vitor (~24), Robinson (~19), Mining Guild (~19), Point Luna (~16), UNMI (~15).
3. **Starting cash is worth 1:1** (no discount even at 60 MC), but **bulk resources are not**: 20 steel is worth ~1.5 each, not 2.
4. **Weak corps are weak because they are thin, not because their ability is bad** (Helion, Inventrix, PhoboLog all have ~60 MC tangible + a small/medium ability). UNMI is the exception: a decent action on almost no body.
5. **Selection bias lesson:** a conditional ability (a discount, a requirement bypass) measures higher as a *card* than as a *corp*, because players buy the card only when they have targets. Earth Office (8.9) vs Teractor (5.7) is the clean example.
6. **Player behaviour is well-calibrated**: keep rates rank almost exactly like measured values. Slight over-keeping: Valley Trust (70%, ranked 5th) and Vitor; slight under-keeping: Interplanetary Cinematics (47%, ranked 4th) and Mining Guild.

## 6. Caveats
- EPM = 0.14 Elo/MC is carried over from the gen-1 project-card analysis; the corp and prelude baselines were both derived under it.
- Hand-strength controls are additive; they cannot remove synergy-based selection (keeping a corp *because* the hand fits it). Discount and requirement abilities are therefore mildly conditional values.
- The alternative estimand (kept vs. offered-but-declined) gives the same ranking but compresses weak corps' deltas toward zero (a weak corp is only kept when the alternative is also weak); it is reported in the spreadsheet as a robustness column, not used for pricing.
- No card tag/cost metadata exists in the dataset, so discount-usage counts (Earth/building/power cards, ≥20 MC plays, events) are inferred from the measured ability, not observed.

## 7. Files
- `corp_values.xlsx` / `corp_values.csv` — the spreadsheet (sheets: Corp values, Tangible breakdown, Constants, Baseline, Raw deltas).
- `corp_hand.py` → `corp_hand_deltas.csv` — the estimator. `corp_specs.py` — tangible content per corp. `solve_corp_baseline.py` — baseline. `corp_table.py` — value table. `export_corp_values.py` — spreadsheet export.
