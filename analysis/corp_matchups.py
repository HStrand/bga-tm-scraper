#!/usr/bin/env python3
"""Corporation matchups: does a corp's Elo gain deviate from its baseline
against specific opponent corps?

Sample: standard-filtered 2p games (handstrength.parquet carries the filter),
both players' corp among the 17 base+Prelude corps. One row per player-game.

Additive model (OLS, HC1):
    EloChange = own-corp FE + opponent-corp FE
              + own/opp HS_prelude + own/opp HS_project  (hand-strength noise control)
Matchup effect(A vs B) = mean residual of A's rows when facing B
    = how much better/worse A does against B than its overall baseline and
      B's overall strength together predict. Antisymmetric by construction
      (EloChange is ~zero-sum in 2p), so effect(B vs A) ~ -effect(A vs B).

Outputs: corp_matchups_long.csv (all ordered pairs), corp_matchups_matrix.csv
(rows = own corp, cols = opponent), printed per-corp summary.

Options: --max-diff D   keep games where |Elo_a - Elo_b| <= D
         --min-avg A / --max-avg B   keep games by average Elo of the two players
         --tag T        suffix for output files (corp_matchups_long_T.csv)
         --brief        print only the top-15 pairs by |z|
"""
import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from corp_specs import CORPS

ap = argparse.ArgumentParser()
ap.add_argument("--max-diff", type=float)
ap.add_argument("--min-avg", type=float)
ap.add_argument("--max-avg", type=float)
ap.add_argument("--tag", default="")
ap.add_argument("--brief", action="store_true")
args = ap.parse_args()
sfx = f"_{args.tag}" if args.tag else ""

here = Path(__file__).parent
d = here / "db_dump"
gp = (d / "gameplayers_canonical.parquet").as_posix()
gps = (d / "gameplayerstats.parquet").as_posix()
hs = (d / "handstrength.parquet").as_posix()

rows = duckdb.sql(f"""
WITH p AS (
  SELECT h.TableId, h.PlayerId, CAST(g.EloChange AS DOUBLE) AS EloChange, g.Elo,
         s.Corporation AS Corp, h.HS_prelude, h.HS_project_total AS HS_project
  FROM '{hs}' h
  JOIN '{gp}' g USING (TableId, PlayerId)
  JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gps}') s USING (TableId, PlayerId)
)
SELECT a.TableId, a.PlayerId, a.EloChange, a.Corp, b.Corp AS Opp,
       abs(a.Elo - b.Elo) AS EloDiff, (a.Elo + b.Elo) / 2.0 AS EloAvg,
       a.HS_prelude, a.HS_project, b.HS_prelude AS Opp_HS_prelude, b.HS_project AS Opp_HS_project
FROM p a JOIN p b ON a.TableId = b.TableId AND a.PlayerId <> b.PlayerId
""").df()
corps = list(CORPS)
rows = rows[rows["Corp"].isin(corps) & rows["Opp"].isin(corps)]
if args.max_diff is not None:
    rows = rows[rows["EloDiff"] <= args.max_diff]
if args.min_avg is not None:
    rows = rows[rows["EloAvg"] >= args.min_avg]
if args.max_avg is not None:
    rows = rows[rows["EloAvg"] < args.max_avg]
rows = rows.reset_index(drop=True)
print(f"rows={len(rows):,}  games={rows['TableId'].nunique():,}")

# ---- additive model --------------------------------------------------------
own = pd.get_dummies(rows["Corp"]).reindex(columns=corps, fill_value=0).to_numpy(float)
opp = pd.get_dummies(rows["Opp"]).reindex(columns=corps, fill_value=0).to_numpy(float)
hsc = rows[["HS_prelude", "HS_project", "Opp_HS_prelude", "Opp_HS_project"]]
hsc = (hsc - hsc.mean()).to_numpy(float)
# drop one dummy per block for identifiability (intercept included)
X = np.column_stack([np.ones(len(rows)), own[:, 1:], opp[:, 1:], hsc])
y = rows["EloChange"].to_numpy(float)
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
rows["resid"] = y - X @ beta

# corp baselines: raw mean EloChange and additive own-effect (relative to mean)
base = rows.groupby("Corp")["EloChange"].agg(["mean", "count"])
own_fe = pd.Series(np.r_[0.0, beta[1:len(corps)]], index=corps)
own_fe -= own_fe.mean()
opp_fe = pd.Series(np.r_[0.0, beta[len(corps):2 * len(corps) - 1]], index=corps)
opp_fe -= opp_fe.mean()

# ---- matchup residuals -----------------------------------------------------
g = rows.groupby(["Corp", "Opp"])["resid"]
long = g.agg(effect="mean", n="count", sd="std").reset_index()
long["se"] = long["sd"] / np.sqrt(long["n"])
long["z"] = long["effect"] / long["se"]
long["raw_mean"] = rows.groupby(["Corp", "Opp"])["EloChange"].mean().to_numpy()
long = long.drop(columns="sd")
long.to_csv(here / f"corp_matchups_long{sfx}.csv", index=False, float_format="%.4f")
mat = long.pivot(index="Corp", columns="Opp", values="effect").reindex(index=corps, columns=corps)
mat.to_csv(here / f"corp_matchups_matrix{sfx}.csv", float_format="%.3f")
zmat = long.pivot(index="Corp", columns="Opp", values="z").reindex(index=corps, columns=corps)

# ---- summary ---------------------------------------------------------------
if args.brief:
    u = long[long["Corp"] < long["Opp"]]
    chi = float((u["z"] ** 2).sum())
    print(f"unique pairs {len(u)}, sum z^2 = {chi:.1f} on {len(u)} df, "
          f"|z|>2: {(u['z'].abs() > 2).sum()}, median SE {u['se'].median():.2f}")
    u = u.reindex(u["z"].abs().sort_values(ascending=False).index).head(15)
    for r in u.itertuples():
        print(f"  {r.Corp:<26} vs {r.Opp:<30} {r.effect:+.2f} +/-{r.se:.2f}  z={r.z:+.1f}  n={int(r.n)}")
    raise SystemExit
print("\nCorp baselines (2p standard filters): raw mean EloChange, additive own-corp "
      "effect (centered), n player-games")
for c in base.sort_values("mean", ascending=False).index:
    print(f"  {c:<32}{base.loc[c,'mean']:>+7.3f}{own_fe[c]:>+8.3f}{int(base.loc[c,'count']):>8}")

nonmirror = long[long["Corp"] != long["Opp"]]
print(f"\nOff-diagonal matchup effects: {len(nonmirror)//2} unique pairs; "
      f"|z|>2: {(nonmirror['z'].abs() > 2).sum()//2}, |z|>3: {(nonmirror['z'].abs() > 3).sum()//2} "
      f"(expect ~{0.046*len(nonmirror)//2:.0f} and ~{0.0027*len(nonmirror)//2:.1f} by chance)")
print(f"SD of off-diagonal effects: {nonmirror['effect'].std():.3f} Elo; "
      f"median SE {nonmirror['se'].median():.3f} Elo")

print("\nPer-corp: worst (nemesis) and best matchups, effect in Elo vs additive expectation")
for c in corps:
    s = nonmirror[nonmirror["Corp"] == c].sort_values("effect")
    w, b = s.iloc[0], s.iloc[-1]
    print(f"\n{c}  (baseline {base.loc[c,'mean']:+.2f})")
    print(f"  nemesis : {w.Opp:<32} {w.effect:+.2f} (z={w.z:+.1f}, n={int(w.n)}, raw {w.raw_mean:+.2f})")
    print(f"  best    : {b.Opp:<32} {b.effect:+.2f} (z={b.z:+.1f}, n={int(b.n)}, raw {b.raw_mean:+.2f})")
    sig = s[s["z"].abs() >= 2]
    if len(sig):
        print("  |z|>=2  : " + "; ".join(f"{r.Opp} {r.effect:+.2f} (z {r.z:+.1f})" for r in sig.itertuples()))

print("\nMatchup matrix (rows = own corp, cols = opponent; Elo vs additive expectation)")
ab = {c: "".join(w[0] for w in c.split())[:4] for c in corps}
pd.set_option("display.width", 250)
m = mat.copy(); m.index = [ab[c] for c in m.index]; m.columns = [ab[c] for c in m.columns]
print(m.round(2).to_string())
print("\nZ matrix")
z = zmat.copy(); z.index = [ab[c] for c in z.index]; z.columns = [ab[c] for c in z.columns]
print(z.round(1).to_string())
