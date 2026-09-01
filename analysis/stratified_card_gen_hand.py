#!/usr/bin/env python3
"""Card gen-N elo delta controlling for corp AND starting-hand strength.

Estimates how much playing a card in gen N changes raw EloChange, via OLS with
corporation fixed effects, then again adding the starting-hand-strength covariate
(HandStrength from build_handstrength.py, leave-one-out for the analyzed card).
The gap between the two = the hand-selection correction.

Reports two estimands side by side:
  1. vs all-not-played   -- control = every other player-game (matches the
                            convention of stratified_card_gen_elo.py).
  2. vs offered-declined -- sample restricted to players who were OFFERED the card;
                            played vs declined. Cleaner: conditions on availability
                            before hand strength is applied.

SEs are HC1 heteroskedasticity-robust (win/loss residuals are not homoskedastic).

Run build_handstrength.py first. Usage:
  python stratified_card_gen_hand.py "Card Name" [gen] [--no-loo]
"""

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

argv = sys.argv[1:]
no_loo = "--no-loo" in argv
argv = [a for a in argv if a != "--no-loo"]
card = argv[0]
gen = int(argv[1]) if len(argv) > 1 else 1
card_sql = card.replace("'", "''")

here = Path(__file__).parent
data_dir = here / "db_dump"
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (data_dir / "gameplayerstats.parquet").as_posix()
gamecards = (data_dir / "gamecards.parquet").as_posix()
sh_card = (data_dir / "startinghandcards.parquet").as_posix()
handstrength = (data_dir / "handstrength.parquet").as_posix()
item_values = (data_dir / "item_values.parquet").as_posix()

# Leave-one-out value of the analyzed card (0 if it never appears as a kept project).
row = duckdb.sql(
    f"SELECT value FROM '{item_values}' WHERE ItemType = 'project' AND Item = '{card_sql}'"
).fetchone()
v_card = float(row[0]) if row else 0.0
if no_loo:
    v_card = 0.0

# One row per standard-filtered 2p player-game: outcome, corp, treatment, offered
# flag and the (full-hand) HandStrength covariate.
query = f"""
SELECT hs.TableId, hs.PlayerId,
       CAST(gp.EloChange AS DOUBLE) AS EloChange,
       gps.Corporation,
       hs.HandStrength,
       EXISTS (
           SELECT 1 FROM '{gamecards}' gc
           WHERE gc.TableId = hs.TableId AND gc.PlayerId = hs.PlayerId
             AND gc.Card = '{card_sql}' AND gc.PlayedGen = {gen}
       ) AS Played,
       EXISTS (
           SELECT 1 FROM '{sh_card}' sc
           WHERE sc.TableId = hs.TableId AND sc.PlayerId = hs.PlayerId
             AND sc.Card = '{card_sql}'
       ) AS Offered
FROM '{handstrength}' hs
JOIN '{gameplayers}' gp USING (TableId, PlayerId)
JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gameplayerstats}') gps
  USING (TableId, PlayerId)
WHERE gps.Corporation IS NOT NULL
"""

df = duckdb.sql(query).df()
df["Played"] = df["Played"].astype(float)
df["Offered"] = df["Offered"].astype(bool)
# Leave-one-out: remove the analyzed card's own contribution where it was offered.
df["HS_LOO"] = df["HandStrength"] - v_card * df["Offered"].astype(float)


def ols_hc1(y, X):
    """OLS via lstsq with HC1 robust covariance. Returns (beta, se)."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    meat = (X * (resid ** 2)[:, None]).T @ X
    cov = XtX_inv @ meat @ XtX_inv * (n / (n - k))
    return beta, np.sqrt(np.diag(cov))


def design(sub, with_hs):
    """Build [const, Played, (HS_LOO_centered), corp dummies] for a subframe."""
    cols = {"const": np.ones(len(sub)), "Played": sub["Played"].to_numpy()}
    names = ["const", "Played"]
    if with_hs:
        cols["HandStrength"] = (sub["HS_LOO"] - sub["HS_LOO"].mean()).to_numpy()
        names.append("HandStrength")
    dummies = pd.get_dummies(sub["Corporation"], prefix="c", drop_first=True)
    for cname in dummies.columns:
        cols[cname] = dummies[cname].to_numpy(dtype=float)
        names.append(cname)
    X = np.column_stack([cols[n] for n in names])
    return X, names


def fit(sub, with_hs):
    X, names = design(sub, with_hs)
    y = sub["EloChange"].to_numpy()
    beta, se = ols_hc1(y, X)
    out = {}
    for key in ("Played", "HandStrength"):
        if key in names:
            i = names.index(key)
            out[key] = (beta[i], se[i])
    return out


def report(name, sub):
    n = len(sub)
    n_pl = int(sub["Played"].sum())
    print(f"\n=== {name} ===")
    print(f"  n = {n:,}  (played in gen {gen}: {n_pl:,};  control: {n - n_pl:,})")
    if n_pl < 20 or (n - n_pl) < 20:
        print("  too few games in one cohort -- skipping")
        return
    a = fit(sub, with_hs=False)
    b = fit(sub, with_hs=True)
    pa, sea = a["Played"]
    pb, seb = b["Played"]
    hb, hse = b["HandStrength"]
    print(f"  corp-FE only            : Played = {pa:+.3f} +/- {sea:.3f} "
          f"(t={pa / sea:+.1f})")
    print(f"  corp-FE + HandStrength  : Played = {pb:+.3f} +/- {seb:.3f} "
          f"(t={pb / seb:+.1f})")
    print(f"  hand-strength correction: {pb - pa:+.3f}")
    print(f"  HandStrength coef       : {hb:+.4f} +/- {hse:.4f} "
          f"(t={hb / hse:+.1f})  [expect >0]")


loo_note = "DISABLED (--no-loo)" if no_loo else f"v_card = {v_card:+.3f}"
print(f"{card}  gen {gen}   leave-one-out: {loo_note}")
print(f"Outcome: raw EloChange. SEs: HC1 robust. Corp fixed effects in all models.")

report("vs all-not-played", df)
report("vs offered-but-declined", df[df["Offered"]].copy())
