#!/usr/bin/env python3
"""Average game-ending generation by map, normalized for player Elo.

Higher-Elo players end games sooner, and the alternate maps skew to stronger
players, so the raw per-map averages are confounded by Elo. This script removes
that confound two ways:

  1. Post-stratification: bin games by mean player Elo, take each map's
     within-bin mean end-gen, then reweight to the POOLED Elo distribution
     (the mix every map would have if Elo were balanced). Nonparametric.
  2. OLS: Generations ~ MeanElo + C(Map). The map coefficients are the
     Elo-adjusted gaps vs the reference map; adjusted means are the fitted
     values at the overall mean Elo.

Standard filters, 2-player, non-conceded.
"""

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

here = Path(__file__).parent
d = here / "db_dump"
games = (d / "games.parquet").as_posix()
gamestats = (d / "gamestats.parquet").as_posix()
gp = (d / "gameplayers_canonical.parquet").as_posix()

MAPS = ["Tharsis", "Hellas", "Elysium", "Vastitas Borealis"]
BIN_WIDTH = 50

maps_in = ", ".join(f"'{m}'" for m in MAPS)
query = f"""
WITH filtered AS (
    SELECT DISTINCT g.TableId, g.Map, gs.Generations
    FROM '{games}' g
    JOIN '{gamestats}' gs USING (TableId)
    WHERE g.ColoniesOn = FALSE
      AND g.PreludeOn = TRUE
      AND g.CorporateEraOn = TRUE
      AND g.GameMode <> 'Friendly mode'
      AND gs.PlayerCount = 2
      AND gs.Conceded = FALSE
      AND g.Map IN ({maps_in})
),
elo AS (
    SELECT TableId, AVG(CAST(Elo AS DOUBLE)) AS MeanElo, COUNT(Elo) AS nElo
    FROM '{gp}'
    GROUP BY TableId
)
SELECT f.Map, f.Generations, e.MeanElo
FROM filtered f
JOIN elo e USING (TableId)
WHERE e.nElo = 2 AND e.MeanElo IS NOT NULL
"""

df = duckdb.sql(query).df()
df["EloBin"] = (np.floor(df["MeanElo"] / BIN_WIDTH) * BIN_WIDTH).astype(int)

# --- Raw means ---
raw = df.groupby("Map").agg(Games=("Generations", "size"),
                            AvgElo=("MeanElo", "mean"),
                            RawEndGen=("Generations", "mean"))

# --- 1. Post-stratification to the pooled Elo distribution ---
# pooled weight per bin = share of all games in that bin
pooled_w = df.groupby("EloBin").size()
pooled_w = pooled_w / pooled_w.sum()

bin_means = df.groupby(["Map", "EloBin"])["Generations"].mean()
adj = {}
for m in MAPS:
    mm = bin_means.loc[m]
    # restrict to bins the map actually has; renormalize pooled weights over them
    common = pooled_w.loc[mm.index]
    w = common / common.sum()
    adj[m] = float((mm * w).sum())
strat = pd.Series(adj, name="StratAdjEndGen")

# --- 2. OLS: Generations ~ MeanElo + C(Map) ---
X_map = pd.get_dummies(df["Map"], prefix="Map").astype(float)
X = pd.concat([pd.Series(1.0, index=df.index, name="const"),
               df["MeanElo"].rename("MeanElo"),
               X_map], axis=1)
# drop one map dummy as reference + drop const collinearity handled via lstsq
ref = f"Map_{MAPS[0]}"
X = X.drop(columns=[ref])
beta, *_ = np.linalg.lstsq(X.values, df["Generations"].values, rcond=None)
coef = dict(zip(X.columns, beta))
mean_elo = df["MeanElo"].mean()
ols_adj = {}
for m in MAPS:
    val = coef["const"] + coef["MeanElo"] * mean_elo
    key = f"Map_{m}"
    if key in coef:
        val += coef[key]
    ols_adj[m] = val
ols = pd.Series(ols_adj, name="OLSAdjEndGen")
elo_per_100 = coef["MeanElo"] * 100

out = raw.join(strat).join(ols)
out = out.reindex(MAPS)
out["AvgElo"] = out["AvgElo"].round(0)
for c in ["RawEndGen", "StratAdjEndGen", "OLSAdjEndGen"]:
    out[c] = out[c].round(2)

print(f"\nElo effect (OLS): {elo_per_100:+.3f} gen per +100 Elo "
      f"(overall mean Elo = {mean_elo:.0f}, n = {len(df):,} games)\n")
print("Avg game-ending generation by map, raw vs Elo-normalized:")
print(out.to_string())
print("\nAdjusted columns put every map on the pooled Elo distribution / common "
      "mean Elo, so they are directly comparable.")
