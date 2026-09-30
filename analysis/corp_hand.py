#!/usr/bin/env python3
"""Hand-strength-controlled delta for KEEPING a corporation.

Corp analog of prelude_hand.py. Treatment = kept this corp from the opening
selection (startinghandcorporations.Kept = TRUE); each player is offered exactly
2 corps and keeps 1, so the delta measures this corp vs the corp it displaces.
Outcome = raw EloChange; HC1 robust SE.

Controls against the ENTIRE offered starting hand as THREE covariates:
  HS_corp_LOO    - the OTHER offered corporation (this corp left out)
  HS_prelude     - all 4 offered preludes
  HS_project     - all 10 offered project cards
NO corp fixed effects -- the corporation IS the treatment.

Two estimands:
  vs all-not-kept        -- control = every other player-game (common baseline =
                            the kept-weighted average corp). STANDARD for the
                            MC conversion (mirrors the prelude convention).
  vs offered-but-declined -- sample = players offered this corp; kept vs took
                            the other one. Baseline differs per corp (a weak corp
                            is only kept when the alternative is also weak), so
                            use as a robustness check, not for pricing.

Run build_handstrength.py first.
Usage: python corp_hand.py                 # all corps -> table + corp_hand_deltas.csv
       python corp_hand.py "Corp Name"     # one corp, verbose
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

here = Path(__file__).parent
d = here / "db_dump"
gameplayers = (d / "gameplayers_canonical.parquet").as_posix()
sh_corp = (d / "startinghandcorporations.parquet").as_posix()
handstrength = (d / "handstrength.parquet").as_posix()
item_values = (d / "item_values.parquet").as_posix()

only = sys.argv[1] if len(sys.argv) > 1 else None

# One row per standard-filtered 2p player-game (handstrength.parquet already
# carries the filter), with outcome and the three hand-strength components.
base = duckdb.sql(f"""
SELECT hs.TableId, hs.PlayerId, CAST(gp.EloChange AS DOUBLE) AS EloChange,
       hs.HS_corp, hs.HS_prelude, hs.HS_project_total
FROM '{handstrength}' hs
JOIN '{gameplayers}' gp USING (TableId, PlayerId)
""").df()

# Offered corps (long): one row per (player-game, corp offered) with Kept flag.
offers = duckdb.sql(f"""
SELECT DISTINCT TableId, PlayerId, Corporation, Kept FROM '{sh_corp}'
""").df()
offers = offers.merge(base[["TableId", "PlayerId"]], on=["TableId", "PlayerId"])

corp_values = dict(duckdb.sql(
    f"SELECT Item, value FROM '{item_values}' WHERE ItemType = 'corp'"
).fetchall())

HS_COLS = ["HS_corp_LOO", "HS_prelude", "HS_project_total"]


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
    b, se = ols_hc1(sub["EloChange"].to_numpy(), np.column_stack(cols))
    return {n: (b[i], se[i]) for i, n in enumerate(names)}


def analyze(corp, verbose):
    o = offers[offers["Corporation"] == corp]
    df = base.merge(o[["TableId", "PlayerId", "Kept"]], on=["TableId", "PlayerId"],
                    how="left")
    df["Offered"] = df["Kept"].notna()
    df["Kept"] = df["Kept"].fillna(False).astype(float)
    # Leave-one-out: keep only the OTHER offered corp in the corp-strength term.
    df["HS_corp_LOO"] = df["HS_corp"] - corp_values.get(corp, 0.0) * df["Offered"]

    out = {"Corporation": corp, "kept": int(df["Kept"].sum()),
           "offered": int(df["Offered"].sum())}
    for label, key, sub in (("all-not-kept", "all", df),
                            ("offered-but-declined", "decl", df[df["Offered"]])):
        nk = int(sub["Kept"].sum())
        if nk < 20 or len(sub) - nk < 20:
            if verbose:
                print(f"\n=== vs {label} ===  too few")
            continue
        a = fit(sub, False)["Kept"]
        b = fit(sub, True)
        out[f"{key}_raw"], out[f"{key}_raw_se"] = a
        out[f"{key}_delta"], out[f"{key}_se"] = b["Kept"]
        if verbose:
            print(f"\n=== vs {label} ===  n={len(sub):,} kept={nk:,} ctrl={len(sub)-nk:,}")
            print(f"  no controls          : Kept = {a[0]:+.3f} +/- {a[1]:.3f}")
            print(f"  + full-hand controls : Kept = {b['Kept'][0]:+.3f} +/- {b['Kept'][1]:.3f}")
            for c in HS_COLS:
                print(f"      {c:<16} coef = {b[c][0]:+.4f} +/- {b[c][1]:.4f}")
    return out


if only:
    print(f"{only}   (corp value in covariate = {corp_values.get(only, 0.0):+.3f})")
    analyze(only, verbose=True)
    sys.exit()

corps = sorted(offers["Corporation"].dropna().unique())
rows = [analyze(c, verbose=False) for c in corps]
res = pd.DataFrame(rows).sort_values("all_delta", ascending=False)

print("Corporations: hand-strength-controlled delta for KEEPING the corp "
      "(raw EloChange, HC1 SE); 2p standard filters, no corp FE.")
print("  all  = vs all-not-kept (+ full-hand controls)   [standard for MC pricing]")
print("  decl = vs offered-but-declined (+ full-hand controls)")
print("  raw  = same estimand with no hand controls\n")
print(f"{'#':>3}  {'Corporation':<32}{'kept%':>6}{'all_raw':>9}{'all':>9}{'+/-SE':>7}"
      f"{'decl_raw':>10}{'decl':>9}{'+/-SE':>7}{'kept':>8}")
for i, r in enumerate(res.itertuples(index=False), 1):
    print(f"{i:>3}  {r.Corporation:<32}{100*r.kept/r.offered:>6.1f}{r.all_raw:>+9.3f}"
          f"{r.all_delta:>+9.3f}{r.all_se:>7.3f}{r.decl_raw:>+10.3f}{r.decl_delta:>+9.3f}"
          f"{r.decl_se:>7.3f}{r.kept:>8}")

out = here / "corp_hand_deltas.csv"
res.to_csv(out, index=False, float_format="%.4f")
print(f"\nWrote {out}")
