#!/usr/bin/env python3
"""Batch hand-strength-controlled gen-N deltas for a list of cards.

For each card prints the corp-FE-only and corp-FE+HandStrength (leave-one-out)
Played coefficient for the all-not-played estimand, plus the offered-but-declined
HS-controlled number. Outcome = raw EloChange, HC1 robust SEs.

Run build_handstrength.py first.
Usage: python hand_table.py [gen]   (reads CARDS list below)
"""

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

gen = int(sys.argv[1]) if len(sys.argv) > 1 else 1

CARDS = [
    "Power Plant", "Geothermal Power", "Giant Space Mirror", "Peroxide Power",
    "Nuclear Power", "Micro-Mills", "Import of Advanced GHG", "Soletta",
    "Adapted Lichen", "Designed Microorganisms", "Lichen", "Search For Life",
    "Trans-Neptune Probe", "Lagrange Observatory", "Inventors' Guild",
    "Business Network", "Building Industries", "Industrial Microbes", "Mine",
    "Asteroid Mining Consortium", "Io Mining Industries", "Asteroid Mining",
    "Titanium Mine", "Vesta Shipyard", "Phobos Space Haven", "Protected Habitats",
    "Pets", "Rover Construction", "Space Station", "Arctic Algae",
    "Viral Enhancers", "Sponsors", "Acquired Company", "Immigration Shuttles",
    "Hackers",
]

here = Path(__file__).parent
data_dir = here / "db_dump"
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (data_dir / "gameplayerstats.parquet").as_posix()
gamecards = (data_dir / "gamecards.parquet").as_posix()
sh_card = (data_dir / "startinghandcards.parquet").as_posix()
handstrength = (data_dir / "handstrength.parquet").as_posix()
item_values = (data_dir / "item_values.parquet").as_posix()

# Base frame shared across cards: filtered player-games with corp + HandStrength.
base = duckdb.sql(f"""
SELECT hs.TableId, hs.PlayerId, CAST(gp.EloChange AS DOUBLE) AS EloChange,
       gps.Corporation, hs.HandStrength
FROM '{handstrength}' hs
JOIN '{gameplayers}' gp USING (TableId, PlayerId)
JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gameplayerstats}') gps
  USING (TableId, PlayerId)
WHERE gps.Corporation IS NOT NULL
""").df()

vals = duckdb.sql(
    f"SELECT Item, value FROM '{item_values}' WHERE ItemType = 'project'"
).df().set_index("Item")["value"].to_dict()


def ols_hc1(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    meat = (X * (resid ** 2)[:, None]).T @ X
    cov = XtX_inv @ meat @ XtX_inv * (n / (n - k))
    return beta, np.sqrt(np.diag(cov))


def played_coef(sub, with_hs):
    cols = [np.ones(len(sub)), sub["Played"].to_numpy()]
    if with_hs:
        cols.append((sub["HS_LOO"] - sub["HS_LOO"].mean()).to_numpy())
    d = pd.get_dummies(sub["Corporation"], drop_first=True).to_numpy(dtype=float)
    X = np.column_stack(cols + [d])
    beta, se = ols_hc1(sub["EloChange"].to_numpy(), X)
    return beta[1], se[1]


rows = []
for card in CARDS:
    csql = card.replace("'", "''")
    flags = duckdb.sql(f"""
    SELECT hs.TableId, hs.PlayerId,
           EXISTS (SELECT 1 FROM '{gamecards}' gc
                   WHERE gc.TableId = hs.TableId AND gc.PlayerId = hs.PlayerId
                     AND gc.Card = '{csql}' AND gc.PlayedGen = {gen}) AS Played,
           EXISTS (SELECT 1 FROM '{sh_card}' sc
                   WHERE sc.TableId = hs.TableId AND sc.PlayerId = hs.PlayerId
                     AND sc.Card = '{csql}') AS Offered
    FROM '{handstrength}' hs
    """).df()
    df = base.merge(flags, on=["TableId", "PlayerId"], how="inner")
    df["Played"] = df["Played"].astype(float)
    v = float(vals.get(card, 0.0))
    df["HS_LOO"] = df["HandStrength"] - v * df["Offered"].astype(float)

    n_pl = int(df["Played"].sum())
    if n_pl < 20:
        rows.append((card, n_pl, None, None, None))
        continue
    a, _ = played_coef(df, with_hs=False)
    b, bse = played_coef(df, with_hs=True)
    off = df[df["Offered"]]
    if int(off["Played"].sum()) >= 20 and (len(off) - int(off["Played"].sum())) >= 20:
        c, _ = played_coef(off, with_hs=True)
    else:
        c = None
    rows.append((card, n_pl, a, (b, bse), c))

print(f"Hand-strength-controlled gen-{gen} Played coefficient (raw EloChange).")
print(f"{'Card':<28}{'n':>7}{'corpFE':>9}{'+HS(all)':>11}{'+/-SE':>7}{'+HS(offered)':>14}")
for card, n_pl, a, b, c in rows:
    if b is None:
        print(f"{card:<28}{n_pl:>7}   (too few)")
        continue
    bval, bse = b
    cstr = f"{c:+.3f}" if c is not None else "  n/a"
    print(f"{card:<28}{n_pl:>7}{a:>+9.3f}{bval:>+11.3f}{bse:>7.3f}{cstr:>14}")
