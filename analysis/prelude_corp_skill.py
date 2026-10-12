#!/usr/bin/env python3
"""Skill expression with vs. without Prelude corporations in Arena.

The Arena season that started 2026-07-15 removed the five Prelude corps.
Compare it (S3) with the two earlier 2026 seasons (S1 from ~Jan 13, S2 from
~Apr 14), which had them. Seasons are cut on TableId (monotone in time;
ParsedDateTime has month/day swaps), at the Arena-point resets.

All measures use only gameplayers (Elo / EloChange), so indexed-but-unscraped
games count too. gameplayers.Elo is post-game; pre-game Elo = Elo - EloChange.

1. Live slope   : logit P(win) = k * ln10/400 * (pre-game Elo diff). k=1 means
                  results are exactly as skill-driven as Elo assumes.
2. Frozen slope : same, but each player's Elo is frozen at the season start
                  (last game before the boundary, >= MIN_PRIOR prior games).
                  Elo can't re-adapt to the new format, so a lower skill cap
                  shows up as a lower k than in the placebo seasons.
3. Top players  : actual vs Elo-expected score for the top frozen-Elo players.
4. BT spread    : random-effects Bradley-Terry fitted within each season;
                  sigma = SD of true skill in Elo points, independent of Elo.
                  Also refitted on a fixed panel of players active in every
                  season, since sigma depends on who is in the sample.

Options: --window W   TableId span per season for the phase-matched sample
                      (default 25e6 ~ first 7 weeks)
         --boot B     bootstrap replicates (default 400)
"""
import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import minimize_scalar
from scipy.sparse.linalg import splu

ap = argparse.ArgumentParser()
ap.add_argument("--window", type=float, default=25e6)
ap.add_argument("--boot", type=int, default=400)
args = ap.parse_args()

SEASONS = {"S1 (Jan, prelude corps)": 789.4e6,
           "S2 (Apr, prelude corps)": 836.5e6,
           "S3 (Jul, no prelude corps)": 883.35e6}
END = 1e12
MIN_PRIOR = 20          # games before the boundary for a frozen Elo to count
C = np.log(10) / 400
rng = np.random.default_rng(0)

d = Path(__file__).parent / "db_dump"
gp = (d / "gameplayers_canonical.parquet").as_posix()
gc = (d / "games_canonical.parquet").as_posix()
gs = (d / "gamestats.parquet").as_posix()

con = duckdb.connect()
games = con.sql(f"""
WITH t AS (SELECT TableId FROM '{gp}' GROUP BY 1 HAVING count(*) = 2)
SELECT a.TableId, a.PlayerId AS A, b.PlayerId AS B,
       a.Elo - a.EloChange AS EloA, b.Elo - b.EloChange AS EloB,
       CASE WHEN a.EloChange <> b.EloChange THEN (a.EloChange > b.EloChange)::int
            WHEN coalesce(a.ArenaPointsChange, 0) <> coalesce(b.ArenaPointsChange, 0)
                 THEN (coalesce(a.ArenaPointsChange, 0) > coalesce(b.ArenaPointsChange, 0))::int
            WHEN s.Winner IN (a.PlayerId, b.PlayerId) THEN (s.Winner = a.PlayerId)::int
       END AS WinA
FROM '{gp}' a JOIN '{gp}' b ON a.TableId = b.TableId AND a.PlayerId < b.PlayerId
JOIN t ON t.TableId = a.TableId
JOIN '{gc}' g ON g.TableId = a.TableId
LEFT JOIN '{gs}' s ON s.TableId = a.TableId
WHERE g.GameMode = 'Arena mode' AND a.TableId >= {min(SEASONS.values())}
""").df().dropna(subset=["WinA"])
# all-mode rating history for frozen Elo
hist = con.sql(f"SELECT TableId, PlayerId, Elo FROM '{gp}' ORDER BY TableId").df()

bounds = list(SEASONS.values()) + [END]


def frozen_elo(boundary):
    h = hist[hist["TableId"] < boundary]
    n = h.groupby("PlayerId").size()
    last = h.groupby("PlayerId")["Elo"].last()
    return last[n >= MIN_PRIOR]


def slope(diff, win):
    """One-parameter logistic fit of win on Elo diff; returns k."""
    x = C * np.asarray(diff, float)
    y = np.asarray(win, float)
    k = 1.0
    for _ in range(30):
        p = 1 / (1 + np.exp(-k * x))
        step = (x * (y - p)).sum() / (x * x * p * (1 - p)).sum()
        k += step
        if abs(step) < 1e-9:
            break
    return k


def slope_ci(diff, win):
    diff, win = np.asarray(diff, float), np.asarray(win, float)
    k = slope(diff, win)
    bs = [slope(diff[i], win[i]) for i in
          (rng.integers(0, len(diff), len(diff)) for _ in range(args.boot))]
    return k, np.std(bs)


def bt_sigma(g):
    """Random-effects Bradley-Terry: skill_i ~ N(0, s^2), logit P(A wins) = skill_A - skill_B.
    s chosen by Laplace-approximated marginal likelihood. Returns SD in Elo points."""
    ids, inv = np.unique(np.concatenate([g["A"], g["B"]]), return_inverse=True)
    n, m = len(ids), len(g)
    ia, ib = inv[:m], inv[m:]
    X = sparse.csr_matrix((np.r_[np.ones(m), -np.ones(m)],
                           (np.r_[np.arange(m), np.arange(m)], np.r_[ia, ib])), shape=(m, n))
    y = g["WinA"].to_numpy(float)

    def neg_ml(log_s):
        s2 = np.exp(2 * log_s)
        u = np.zeros(n)
        for _ in range(50):
            p = 1 / (1 + np.exp(-(X @ u)))
            grad = X.T @ (y - p) - u / s2
            H = (X.T @ sparse.diags(p * (1 - p)) @ X + sparse.eye(n) / s2).tocsc()
            lu = splu(H)
            du = lu.solve(grad)
            u += du
            if np.abs(du).max() < 1e-7:
                break
        p = np.clip(1 / (1 + np.exp(-(X @ u))), 1e-12, 1 - 1e-12)
        ll = (y * np.log(p) + (1 - y) * np.log(1 - p)).sum()
        logdet = np.log(np.abs(lu.U.diagonal())).sum() + np.log(np.abs(lu.L.diagonal())).sum()
        return -(ll - (u @ u) / (2 * s2) - n * log_s - 0.5 * logdet)

    r = minimize_scalar(neg_ml, bounds=(np.log(0.05), np.log(3)), method="bounded",
                        options={"xatol": 1e-3})
    # SE from the curvature of the marginal likelihood in log s (delta method)
    h = 0.05
    curv = (neg_ml(r.x + h) - 2 * r.fun + neg_ml(r.x - h)) / h ** 2
    sig = np.exp(r.x) / C
    return sig, sig / np.sqrt(max(curv, 1e-9)), n


def report(label, window):
    print(f"\n{'=' * 78}\n{label}\n{'=' * 78}")
    out = []
    for i, (name, lo) in enumerate(SEASONS.items()):
        hi = min(bounds[i + 1], lo + window)
        g = games[(games["TableId"] >= lo) & (games["TableId"] < hi)].reset_index(drop=True)
        diff = g["EloA"] - g["EloB"]
        k_live, se_live = slope_ci(diff, g["WinA"])
        fav = np.where(diff != 0, (diff > 0) == (g["WinA"] == 1), np.nan)

        fz = frozen_elo(lo)
        f = g[g["A"].isin(fz.index) & g["B"].isin(fz.index)].reset_index(drop=True)
        fa, fb = f["A"].map(fz).to_numpy(float), f["B"].map(fz).to_numpy(float)
        fdiff = fa - fb
        k_fz, se_fz = slope_ci(fdiff, f["WinA"])
        big = np.abs(fdiff) >= 150
        fav150 = ((fdiff[big] > 0) == (f["WinA"][big] == 1)).mean()

        # top frozen-Elo players active this season: actual vs Elo-expected score
        long = pd.DataFrame({"P": np.r_[f["A"], f["B"]], "own": np.r_[fa, fb], "opp": np.r_[fb, fa],
                             "win": np.r_[f["WinA"], 1 - f["WinA"]]})
        long["exp"] = 1 / (1 + 10 ** (-(long["own"] - long["opp"]) / 400))
        act = long.groupby("P").agg(own=("own", "first"), n=("win", "size"))
        top = act[act["n"] >= 10].nlargest(100, "own").index
        t = long[long["P"].isin(top)]

        sig, sig_se, npl = bt_sigma(g)
        out.append({"season": name, "games": len(g), "players": npl,
                    "fav win%": 100 * np.nanmean(fav),
                    "k live": f"{k_live:.3f} ±{se_live:.3f}",
                    "frozen games": len(f),
                    "k frozen": f"{k_fz:.3f} ±{se_fz:.3f}",
                    "fav win% (gap>=150)": f"{100 * fav150:.1f} (n={big.sum()})",
                    "top100 win%": 100 * t["win"].mean(),
                    "top100 exp%": 100 * t["exp"].mean(),
                    "top100 games": len(t),
                    "BT sigma (Elo)": f"{sig:.0f} ±{sig_se:.0f}"})
    print(pd.DataFrame(out).set_index("season").T.to_string(float_format=lambda v: f"{v:.1f}"))


report(f"Phase-matched: first {args.window / 1e6:.0f}M table ids of each season", args.window)
report("Full seasons (S3 still running)", END)

# ---- BT spread on a fixed panel (same players in every season) ---------------
wins = [games[(games["TableId"] >= lo) & (games["TableId"] < min(bounds[i + 1], lo + args.window))]
        for i, lo in enumerate(SEASONS.values())]
for min_games in (10, 25):
    panel = None
    for g in wins:
        c = pd.concat([g["A"], g["B"]]).value_counts()
        ok = set(c[c >= min_games].index)
        panel = ok if panel is None else panel & ok
    print(f"\nBT sigma, games between the {len(panel)} players with >= {min_games} games in every phase-matched window")
    for name, g in zip(SEASONS, wins):
        g = g[g["A"].isin(panel) & g["B"].isin(panel)].reset_index(drop=True)
        sig, se, _ = bt_sigma(g)
        print(f"  {name:28s} games={len(g):5d}  sigma={sig:.0f} ±{se:.0f}")

# ---- frozen-Elo win rate by gap band, phase-matched ---------------------------
print(f"\nFavourite win % by frozen-Elo gap (phase-matched)")
rows = {}
for i, (name, lo) in enumerate(SEASONS.items()):
    hi = min(bounds[i + 1], lo + args.window)
    fz = frozen_elo(lo)
    f = games[(games["TableId"] >= lo) & (games["TableId"] < hi)
              & games["A"].isin(fz.index) & games["B"].isin(fz.index)]
    fdiff = (f["A"].map(fz) - f["B"].map(fz)).to_numpy(float)
    favwin = (fdiff > 0) == (f["WinA"].to_numpy() == 1)
    band = pd.cut(np.abs(fdiff), [0, 50, 100, 150, 200, 300, 2000], right=False)
    ok = fdiff != 0
    t = pd.DataFrame({"band": band[ok], "w": favwin[ok]}).groupby("band", observed=True)["w"].agg(["mean", "size"])
    rows[name] = (100 * t["mean"]).round(1).astype(str) + " (" + t["size"].astype(str) + ")"
print(pd.DataFrame(rows).to_string())
