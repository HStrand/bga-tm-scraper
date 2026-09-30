# Corporation matchups (2p, base + Prelude, standard filters)

Question: does a corporation's average Elo gain deviate from its baseline when facing a specific opponent corp?

**Answer: essentially no.** Corporation strength is additive. After accounting for each corp's own strength and the opponent's strength, the residual matchup effects are indistinguishable from sampling noise.

## Method
- 155,684 games / 311,368 player-games (standard filters: 2p, Prelude on, Corporate Era on, no Colonies, no Friendly mode, no Amazonis), both corps among the 17 base+Prelude corps.
- OLS: EloChange = own-corp effect + opponent-corp effect + both players' prelude and project hand strength (noise control).
- Matchup effect(A vs B) = mean residual of A's rows against B. Antisymmetric: effect(B vs A) = -effect(A vs B).
- Script: `analysis/corp_matchups.py`; outputs `corp_matchups_long.csv` (all ordered pairs, effect / se / z / n / raw mean) and `corp_matchups_matrix.csv`.

## Global evidence
| Statistic | Value |
|---|---|
| Unique corp pairs | 136 |
| Pairs with abs(z) > 2 (expected by chance) | 10 (6) |
| Pairs with abs(z) > 3 (expected by chance) | 1 (0.4) |
| Global chi-square test of any matchup effect | p = 0.06 |
| Estimated true matchup SD (after removing sampling noise) | 0.06 Elo |
| Median SE of a single pair | 0.22 Elo |
| Spread of corp main effects (Point Luna to UNMI) | 2.7 Elo |
| Split-half correlation of pair effects (odd vs even TableId) | -0.06 |

The true matchup variation is roughly 40x smaller than the corp-strength variation, and pair estimates from one half of the data do not predict the other half at all. Shrinkage (empirical-Bayes) estimates of every pair are within +/-0.06 Elo.

## Pairs that at least replicate in sign across both halves
These are the only candidates worth watching; none survives a multiple-comparison correction on its own.

| Pair | Full-data effect | Half A | Half B |
|---|---|---|---|
| Ecoline vs Vitor | -0.69 (z -3.7) | -0.59 (z -2.2) | -0.79 (z -3.0) |
| Helion vs Point Luna | +0.68 (z +3.2) | +0.61 (z +1.9) | +0.76 (z +2.7) |
| PhoboLog vs Valley Trust | +0.63 (z +2.8) | +0.52 (z +1.6) | +0.73 (z +2.4) |
| Saturn Systems vs Valley Trust | +0.47 (z +2.5) | +0.50 (z +2.0) | +0.43 (z +1.6) |
| Robinson Industries vs ThorGate | -0.95 (z -2.6) | -0.67 (z -1.4) | -1.20 (z -2.3) |

Ecoline vs Vitor is the strongest single result (the only pair beyond z 3, replicating in both halves). Even so, -0.7 Elo per game is small next to Ecoline's +0.28 baseline and Vitor's +0.39; in matchup terms Ecoline still expects roughly -0.8 Elo per game vs Vitor rather than the -0.1 additive prediction.

## Per-corp summary (largest deviations, raw point estimates)
Baseline = raw mean EloChange per game. Effect = Elo per game vs the additive expectation. Treat everything with abs(z) < 3 as noise.

| Corp | Baseline | Worst matchup | Effect | Best matchup | Effect |
|---|---|---|---|---|---|
| Point Luna | +0.97 | Helion | -0.60 (z -2.9, n=1387) | Vitor | +0.39 (z +2.2, n=2317) |
| Cheung Shing Mars | +0.60 | ThorGate | -0.33 (z -1.0, n=484) | PhoboLog | +0.36 (z +1.5, n=923) |
| Interplanetary Cinematics | +0.58 | PhoboLog | -0.37 (z -1.3, n=721) | Tharsis Republic | +0.26 (z +1.2, n=1287) |
| Saturn Systems | +0.57 | ThorGate | -0.49 (z -1.6, n=495) | Valley Trust | +0.47 (z +2.5, n=1882) |
| Valley Trust | +0.42 | PhoboLog | -0.64 (z -2.8, n=1037) | Helion | +0.41 (z +1.9, n=1247) |
| Vitor | +0.39 | Saturn Systems | -0.50 (z -2.6, n=1755) | Ecoline | +0.71 (z +3.6, n=1697) |
| CrediCor | +0.32 | United Nations Mars Initiative | -0.62 (z -2.0, n=567) | Ecoline | +0.30 (z +1.5, n=1708) |
| Ecoline | +0.28 | Vitor | -0.69 (z -3.7, n=1697) | Inventrix | +0.31 (z +1.3, n=1136) |
| Mining Guild | +0.21 | PhoboLog | -0.47 (z -1.7, n=789) | ThorGate | +0.58 (z +1.4, n=388) |
| Tharsis Republic | +0.05 | PhoboLog | -0.45 (z -1.8, n=850) | ThorGate | +0.47 (z +1.2, n=410) |
| Teractor | +0.00 | Saturn Systems | -0.14 (z -0.7, n=1315) | PhoboLog | +0.39 (z +1.5, n=747) |
| Robinson Industries | -0.26 | ThorGate | -0.95 (z -2.6, n=310) | PhoboLog | +0.53 (z +1.7, n=590) |
| Inventrix | -0.89 | Tharsis Republic | -0.36 (z -1.6, n=1052) | United Nations Mars Initiative | +0.42 (z +1.1, n=332) |
| PhoboLog | -0.89 | Saturn Systems | -0.54 (z -2.3, n=923) | Valley Trust | +0.63 (z +2.8, n=1037) |
| Helion | -0.94 | Ecoline | -0.44 (z -2.1, n=1112) | Point Luna | +0.68 (z +3.2, n=1387) |
| ThorGate | -1.35 | Helion | -0.62 (z -1.4, n=265) | Robinson Industries | +0.76 (z +2.1, n=310) |
| United Nations Mars Initiative | -1.73 | Mining Guild | -0.37 (z -1.2, n=461) | CrediCor | +0.64 (z +1.9, n=567) |

## Interpretation
- Corps do not have archnemeses in the 2p Elo data. Whatever you gain or lose against a specific opponent corp is explained by the two corps' individual strengths.
- This is plausible mechanically: in 2p Terraforming Mars the corps rarely interact directly. The candidate effects that replicate (Ecoline vs Vitor, Helion vs Point Luna) have no obvious mechanism and may still be chance.
- For pricing / presentations, use the additive corp values (corp_values.xlsx). Do not add matchup adjustments.
