#!/usr/bin/env python3
"""Hand-strength-controlled Dust Seals (1 VP) delta at gen 1 and gen 2, in three
cost contexts, to re-derive the gen-1 value of a VP.

Contexts (all buy exactly 1 VP via Dust Seals, at different effective cost):
  full   = any corp, full price 5 MC (printed 2 + 3 buy)
  vitor  = Vitor corp (refunds 3 MC on a VP card) -> effective 2 MC
  ec     = Earth Catapult in play by that gen (-2 MC card cost) -> effective 3 MC

Within each context: OLS EloChange ~ DustSeals_played(gen) + HS_corp +
HS_prelude + HS_project_LOO + corp FE (corp FE dropped for single-corp Vitor).
HC1 SE. Dust Seals is a trap-filler, so delta = 0.14*(VP - cost) + F (selection).
"""
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

d = Path(__file__).parent / "db_dump"
gp = (d / "gameplayers_canonical.parquet").as_posix()
gps = (d / "gameplayerstats.parquet").as_posix()
gc = (d / "gamecards.parquet").as_posix()
hs = (d / "handstrength.parquet").as_posix()
iv = (d / "item_values.parquet").as_posix()
shc = (d / "startinghandcards.parquet").as_posix()

v_ds = float(duckdb.sql(
    f"SELECT value FROM '{iv}' WHERE ItemType='project' AND Item='Dust Seals'").fetchone()[0])

df = duckdb.sql(f"""
SELECT h.TableId, h.PlayerId, CAST(p.EloChange AS DOUBLE) AS Elo,
       s.Corporation, h.HS_corp, h.HS_prelude, h.HS_project_total,
       (s.Corporation = 'Vitor') AS Vitor,
       EXISTS(SELECT 1 FROM '{gc}' c WHERE c.TableId=h.TableId AND c.PlayerId=h.PlayerId
              AND c.Card='Dust Seals' AND c.PlayedGen=1) AS DS1,
       EXISTS(SELECT 1 FROM '{gc}' c WHERE c.TableId=h.TableId AND c.PlayerId=h.PlayerId
              AND c.Card='Dust Seals' AND c.PlayedGen=2) AS DS2,
       EXISTS(SELECT 1 FROM '{gc}' c WHERE c.TableId=h.TableId AND c.PlayerId=h.PlayerId
              AND c.Card='Earth Catapult' AND c.PlayedGen<=1) AS EC1,
       EXISTS(SELECT 1 FROM '{gc}' c WHERE c.TableId=h.TableId AND c.PlayerId=h.PlayerId
              AND c.Card='Earth Catapult' AND c.PlayedGen<=2) AS EC2,
       EXISTS(SELECT 1 FROM '{shc}' x WHERE x.TableId=h.TableId AND x.PlayerId=h.PlayerId
              AND x.Card='Dust Seals') AS OfferedDS
FROM '{hs}' h
JOIN '{gp}' p USING (TableId, PlayerId)
JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gps}') s USING (TableId, PlayerId)
WHERE s.Corporation IS NOT NULL
""").df()
for c in ["Vitor", "DS1", "DS2", "EC1", "EC2", "OfferedDS"]:
    df[c] = df[c].astype(bool)
df["HS_proj_LOO"] = df["HS_project_total"] - v_ds * df["OfferedDS"].astype(float)


def ols_hc1(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    inv = np.linalg.inv(X.T @ X)
    cov = inv @ ((X * (r ** 2)[:, None]).T @ X) @ inv * (len(y) / (len(y) - X.shape[1]))
    return b, np.sqrt(np.diag(cov))


def delta(sub, treat, corp_fe):
    sub = sub.copy()
    cols = [np.ones(len(sub)), sub[treat].astype(float).to_numpy()]
    for c in ["HS_corp", "HS_prelude", "HS_proj_LOO"]:
        cols.append((sub[c] - sub[c].mean()).to_numpy())
    if corp_fe:
        dm = pd.get_dummies(sub["Corporation"], drop_first=True).to_numpy(dtype=float)
        cols.append(dm)
    X = np.column_stack(cols)
    b, se = ols_hc1(sub["Elo"].to_numpy(), X)
    return b[1], se[1], int(sub[treat].sum())


EPM = 0.14
print(f"Dust Seals = 1 VP. Hand-controlled delta; VP_implied = cost + delta/EPM "
      f"(contaminated by trap-filler F).\n")
print(f"{'Context':<22}{'cost':>5}{'gen':>4}{'n':>7}{'delta':>9}{'+/-SE':>8}{'VP_impl':>9}")
rows = [
    ("full price", 5, "DS1", df[~df.Vitor & ~df.EC1], True),
    ("full price", 5, "DS2", df[~df.Vitor & ~df.EC2], True),
    ("Vitor (refund 3)", 2, "DS1", df[df.Vitor], False),
    ("Vitor (refund 3)", 2, "DS2", df[df.Vitor], False),
    ("Earth Catapult (-2)", 3, "DS1", df[df.EC1], True),
    ("Earth Catapult (-2)", 3, "DS2", df[df.EC2], True),
]
for name, cost, treat, sub, fe in rows:
    g = treat[-1]
    b, se, n = delta(sub, treat, fe)
    print(f"{name:<22}{cost:>5}{g:>4}{n:>7}{b:>+9.3f}{se:>8.3f}{cost + b / EPM:>9.2f}")
