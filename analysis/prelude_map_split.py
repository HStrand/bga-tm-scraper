#!/usr/bin/env python3
"""Hand-strength-controlled KEEP delta for a prelude, split by MAP (Tharsis vs
Hellas+Elysium). Tests whether ocean preludes over-perform on Tharsis (premium
2-card ocean placement bonus). Outcome raw EloChange; corp FE + full-hand
controls (HS_corp, HS_prelude_LOO, HS_project_total); HC1 SE.

Usage: python prelude_map_split.py "Prelude Name"
"""
import sys
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

prelude = sys.argv[1]
psql = prelude.replace("'", "''")
d = Path(__file__).parent / "db_dump"
gameplayers = (d / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (d / "gameplayerstats.parquet").as_posix()
games = (d / "games.parquet").as_posix()
sh_prelude = (d / "startinghandpreludes.parquet").as_posix()
handstrength = (d / "handstrength.parquet").as_posix()
item_values = (d / "item_values.parquet").as_posix()

row = duckdb.sql(
    f"SELECT value FROM '{item_values}' WHERE ItemType='prelude' AND Item='{psql}'"
).fetchone()
v_prelude = float(row[0]) if row else 0.0

df = duckdb.sql(f"""
SELECT hs.TableId, hs.PlayerId, CAST(gp.EloChange AS DOUBLE) AS EloChange,
       gps.Corporation, hs.HS_corp, hs.HS_prelude, hs.HS_project_total, g.Map,
       EXISTS (SELECT 1 FROM '{sh_prelude}' sp
               WHERE sp.TableId=hs.TableId AND sp.PlayerId=hs.PlayerId
                 AND sp.Prelude='{psql}' AND sp.Kept=TRUE) AS Kept
FROM '{handstrength}' hs
JOIN '{gameplayers}' gp USING (TableId, PlayerId)
JOIN (SELECT DISTINCT TableId, Map FROM '{games}') g USING (TableId)
JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gameplayerstats}') gps
  USING (TableId, PlayerId)
WHERE gps.Corporation IS NOT NULL
""").df()
df["Kept"] = df["Kept"].astype(float)
df["Offered"] = 0.0  # not needed for all-not-kept; LOO uses kept membership
df["HS_prelude_LOO"] = df["HS_prelude"] - v_prelude * df["Kept"]
HS = ["HS_corp", "HS_prelude_LOO", "HS_project_total"]


def ols_hc1(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    inv = np.linalg.inv(X.T @ X)
    cov = inv @ ((X * (r ** 2)[:, None]).T @ X) @ inv * (len(y) / (len(y) - X.shape[1]))
    return beta, np.sqrt(np.diag(cov))


def kept_coef(sub):
    cols = [np.ones(len(sub)), sub["Kept"].to_numpy()]
    for c in HS:
        cols.append((sub[c] - sub[c].mean()).to_numpy())
    dm = pd.get_dummies(sub["Corporation"], drop_first=True).to_numpy(dtype=float)
    b, se = ols_hc1(sub["EloChange"].to_numpy(), np.column_stack(cols + [dm]))
    return b[1], se[1]


print(f"{prelude}: hand-controlled KEEP delta by map (all-not-kept)\n")
print(f"{'Map group':<22}{'kept n':>8}{'delta':>9}{'+/-SE':>8}")
for label, mask in [
    ("Tharsis", df["Map"] == "Tharsis"),
    ("Hellas+Elysium", df["Map"] != "Tharsis"),
]:
    sub = df[mask]
    nk = int(sub["Kept"].sum())
    b, se = kept_coef(sub)
    print(f"{label:<22}{nk:>8}{b:>+9.3f}{se:>8.3f}")

# map breakdown of available maps for sanity
print("\nmaps present:",
      duckdb.sql(f"SELECT Map, COUNT(*) FROM '{games}' "
                 f"GROUP BY Map ORDER BY 2 DESC").df().to_string(index=False))
