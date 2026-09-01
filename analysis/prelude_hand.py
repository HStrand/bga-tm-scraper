#!/usr/bin/env python3
"""Hand-strength-controlled gen-1 delta for KEEPING a prelude.

Treatment = kept this prelude from the opening selection
(startinghandpreludes.Kept = TRUE). Control = didn't keep it. Since every player
keeps 2 of 4 offered preludes, the delta measures this prelude vs the marginal
prelude it displaces. Outcome = raw EloChange; HC1 robust SE.

Controls against the ENTIRE offered starting hand as THREE separate covariates:
  HS_corp        - both offered corporations
  HS_prelude_LOO - the other 3 offered preludes (this prelude left out)
  HS_project     - all 10 offered project cards
plus corp fixed effects.

Two estimands: vs all-not-kept, and vs offered-but-declined.
Run build_handstrength.py first. Usage: python prelude_hand.py "Prelude Name"
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

prelude = sys.argv[1]
psql = prelude.replace("'", "''")

here = Path(__file__).parent
d = here / "db_dump"
gameplayers = (d / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (d / "gameplayerstats.parquet").as_posix()
sh_prelude = (d / "startinghandpreludes.parquet").as_posix()
handstrength = (d / "handstrength.parquet").as_posix()
item_values = (d / "item_values.parquet").as_posix()

row = duckdb.sql(
    f"SELECT value FROM '{item_values}' WHERE ItemType='prelude' AND Item='{psql}'"
).fetchone()
v_prelude = float(row[0]) if row else 0.0

df = duckdb.sql(f"""
SELECT hs.TableId, hs.PlayerId, CAST(gp.EloChange AS DOUBLE) AS EloChange,
       gps.Corporation, hs.HS_corp, hs.HS_prelude, hs.HS_project_total,
       EXISTS (SELECT 1 FROM '{sh_prelude}' sp
               WHERE sp.TableId=hs.TableId AND sp.PlayerId=hs.PlayerId
                 AND sp.Prelude='{psql}' AND sp.Kept=TRUE) AS Kept,
       EXISTS (SELECT 1 FROM '{sh_prelude}' sp
               WHERE sp.TableId=hs.TableId AND sp.PlayerId=hs.PlayerId
                 AND sp.Prelude='{psql}') AS Offered
FROM '{handstrength}' hs
JOIN '{gameplayers}' gp USING (TableId, PlayerId)
JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gameplayerstats}') gps
  USING (TableId, PlayerId)
WHERE gps.Corporation IS NOT NULL
""").df()
df["Kept"] = df["Kept"].astype(float)
df["Offered"] = df["Offered"].astype(bool)
# Leave-one-out: remove this prelude from the prelude-strength component.
df["HS_prelude_LOO"] = df["HS_prelude"] - v_prelude * df["Offered"].astype(float)
HS_COLS = ["HS_corp", "HS_prelude_LOO", "HS_project_total"]


def ols_hc1(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    inv = np.linalg.inv(X.T @ X)
    cov = inv @ ((X * (resid ** 2)[:, None]).T @ X) @ inv * (n / (n - k))
    return beta, np.sqrt(np.diag(cov))


def fit(sub, with_hs):
    cols = [np.ones(len(sub)), sub["Kept"].to_numpy()]
    names = ["const", "Kept"]
    if with_hs:
        for c in HS_COLS:
            cols.append((sub[c] - sub[c].mean()).to_numpy())
            names.append(c)
    dm = pd.get_dummies(sub["Corporation"], drop_first=True)
    for c in dm.columns:
        cols.append(dm[c].to_numpy(dtype=float)); names.append(c)
    b, se = ols_hc1(sub["EloChange"].to_numpy(), np.column_stack(cols))
    return {n: (b[i], se[i]) for i, n in enumerate(names)}


def report(name, sub):
    nk = int(sub["Kept"].sum())
    print(f"\n=== {name} ===  n={len(sub):,} kept={nk:,} ctrl={len(sub)-nk:,}")
    if nk < 20 or len(sub) - nk < 20:
        print("  too few"); return
    a = fit(sub, False)["Kept"]
    b = fit(sub, True)
    print(f"  corp-FE only         : Kept = {a[0]:+.3f} +/- {a[1]:.3f}")
    print(f"  + full-hand controls : Kept = {b['Kept'][0]:+.3f} +/- {b['Kept'][1]:.3f}")
    for c in HS_COLS:
        print(f"      {c:<16} coef = {b[c][0]:+.4f} +/- {b[c][1]:.4f}")


print(f"{prelude}   (prelude value in covariate = {v_prelude:+.3f})")
report("vs all-not-kept", df)
report("vs offered-but-declined", df[df["Offered"]].copy())
