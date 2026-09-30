#!/usr/bin/env python3
"""Card timing: early vs late value of every project card, adjusted for play rate.

Sample: standard-filtered 2p games (handstrength.parquet carries the filter).

For each card and generation g:
  held_g        players holding the card unplayed at the start of gen g
                (acquired at gen <= g, not played before g, game reached g)
  rate_g        share of holders who play it in gen g  (plays_g / held_g)
  played_g      mean residual Elo of the players who play it in gen g, where the
                residual removes corp fixed effects and both hand-strength
                controls (HS_prelude, HS_project_total), with the card's own
                starting-hand value left out of the control (leave-one-out)
  rel_delta_g   played_g minus the same quantity for ALL card plays in gen g
                (playing anything late is worth ~+0.45 Elo on its own)
  log_rr_g      ln(rate_g / rate_all_g), the card's play rate relative to the
                average card at that gen
  score_g       rel_delta_g + k * log_rr_g

Windows (early = gens 1-4, late = gens 9-12 by default) pool the gens, and
k is set so rel_delta and log_rr have equal spread across cards. Quadrants
come from the signs of score_early and score_late.

Outputs: card_timing_gen.csv, card_timing_matrix.csv, printed summary.
"""
import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--early", nargs=2, type=int, default=[1, 4])
ap.add_argument("--late", nargs=2, type=int, default=[9, 12])
ap.add_argument("--max-gen", type=int, default=12)
ap.add_argument("--min-plays", type=int, default=200, help="per window, for k and quadrants")
ap.add_argument("--k", type=float, help="override the auto-calibrated k")
ap.add_argument("--out-dir", default=None)
args = ap.parse_args()

here = Path(__file__).parent
out = Path(args.out_dir) if args.out_dir else here
d = here / "db_dump"
P = lambda n: (d / n).as_posix()

preludes = json.load(open(here / "preludes.json"))["preludes"]
excl = ",".join("'" + s.replace("'", "''") + "'" for s in preludes)

con = duckdb.connect()
con.sql("SET enable_progress_bar=false")

# 1. players ---------------------------------------------------------------
con.sql(f"""
CREATE TEMP TABLE players AS
SELECT hs.TableId, hs.PlayerId, CAST(gp.EloChange AS DOUBLE) AS Elo,
       gps.Corporation AS Corp, gs.Generations, hs.HS_prelude, hs.HS_project_total AS HS_project
FROM '{P("handstrength.parquet")}' hs
JOIN '{P("gameplayers_canonical.parquet")}' gp USING (TableId, PlayerId)
JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{P("gameplayerstats.parquet")}') gps
     USING (TableId, PlayerId)
JOIN '{P("gamestats.parquet")}' gs USING (TableId)
WHERE gp.EloChange IS NOT NULL AND gps.Corporation IS NOT NULL AND gs.Generations IS NOT NULL
""")
pl = con.sql("SELECT * FROM players").df()
print(f"player-games: {len(pl):,}")

# 2. residualise: Elo ~ corp FE + hand strength ----------------------------
X = pd.get_dummies(pl["Corp"], dtype=float)
X["HS_prelude"] = pl["HS_prelude"].fillna(0.0)
X["HS_project"] = pl["HS_project"].fillna(0.0)
beta, *_ = np.linalg.lstsq(X.values, pl["Elo"].values, rcond=None)
pl["R"] = pl["Elo"].values - X.values @ beta
beta_hs = float(beta[list(X.columns).index("HS_project")])
print(f"HS_project coefficient = {beta_hs:.3f}")
con.register("resid", pl[["TableId", "PlayerId", "R", "Generations"]])
con.sql("CREATE TEMP TABLE pr AS SELECT * FROM resid")
# leave-one-out: HS_project_total includes the analysed card's own starting-hand
# value whenever it was offered, so add that share back for those player-games
con.sql(f"""
CREATE TEMP TABLE offered AS
SELECT DISTINCT sc.TableId, sc.PlayerId, sc.Card, {beta_hs} * iv.value AS loo
FROM '{P("startinghandcards.parquet")}' sc
JOIN '{P("item_values.parquet")}' iv ON iv.ItemType = 'project' AND iv.Item = sc.Card
""")

# 3. cards: one row per (game, player, card) --------------------------------
corps = ",".join("'" + c.replace("'", "''") + "'"
                 for c in con.sql("SELECT DISTINCT Corp FROM players").df()["Corp"].dropna())
con.sql(f"""
CREATE TEMP TABLE cards AS
SELECT gc.TableId, gc.PlayerId, gc.Card,
       MIN(COALESCE(gc.KeptGen, gc.BoughtGen)) AS acq, MIN(gc.PlayedGen) AS played
FROM '{P("gamecards.parquet")}' gc JOIN pr USING (TableId, PlayerId)
WHERE COALESCE(gc.KeptGen, gc.BoughtGen) IS NOT NULL
  AND NOT starts_with(LOWER(gc.Card), 'a card') AND NOT starts_with(LOWER(gc.Card), 'card ')
  AND NOT starts_with(LOWER(gc.Card), 'card_')
  AND LOWER(gc.Card) NOT LIKE '%(no undo beyond this point)%'
  AND gc.Card NOT IN ('Power plant', 'Greenery', 'City', 'Sell patents', 'Aquifer')
  AND gc.Card NOT IN ({excl}) AND gc.Card NOT IN ({corps})
GROUP BY 1, 2, 3
""")

# 4-5. held cohort per (card, gen) and all-card baselines --------------------
G = args.max_gen
con.sql(f"CREATE TEMP TABLE gens AS SELECT range AS g FROM range(1, {G + 1})")
con.sql("""
CREATE TEMP TABLE held AS
SELECT c.Card, gens.g, pr.R + COALESCE(o.loo, 0.0) AS R, (c.played = gens.g) AS play_now
FROM cards c JOIN pr USING (TableId, PlayerId)
LEFT JOIN offered o ON o.TableId = c.TableId AND o.PlayerId = c.PlayerId AND o.Card = c.Card
JOIN gens ON gens.g BETWEEN c.acq AND pr.Generations
         AND (c.played IS NULL OR c.played >= gens.g)
""")
allg = con.sql("""
SELECT g, COUNT(*) AS held_all, COUNT(*) FILTER (WHERE play_now) AS plays_all,
       AVG(R) FILTER (WHERE play_now) AS played_all
FROM held GROUP BY g ORDER BY g
""").df()
allg["rate_all"] = allg["plays_all"] / allg["held_all"]
cg = con.sql("""
SELECT Card, g, COUNT(*) AS n_held, COUNT(*) FILTER (WHERE play_now) AS n_played,
       AVG(R) FILTER (WHERE play_now) AS played_mean,
       STDDEV(R) FILTER (WHERE play_now) AS sd_played
FROM held GROUP BY 1, 2
""").df()
cg = cg.merge(allg[["g", "rate_all", "played_all"]], on="g")
cg["rate"] = cg["n_played"] / cg["n_held"]
cg["se"] = cg["sd_played"] / np.sqrt(cg["n_played"].clip(lower=1))
cg["rel_delta"] = cg["played_mean"] - cg["played_all"]
cg["log_rr"] = np.where(cg["n_played"] > 0, np.log(cg["rate"].clip(lower=1e-12) / cg["rate_all"]), np.nan)
cg = cg.sort_values(["Card", "g"])

# 6. windows ---------------------------------------------------------------
def window(lo, hi, name):
    w = cg[(cg["g"] >= lo) & (cg["g"] <= hi)].copy()
    a = allg[(allg["g"] >= lo) & (allg["g"] <= hi)]
    rate_all_w = a["plays_all"].sum() / a["held_all"].sum()
    w["wd"] = w["n_played"] * w["rel_delta"]
    w["wv"] = (w["n_played"] * w["se"]) ** 2
    s = w.groupby("Card").agg(n_held=("n_held", "sum"), n_played=("n_played", "sum"),
                              wd=("wd", "sum"), wv=("wv", "sum"))
    s["rel_delta"] = s["wd"] / s["n_played"]
    s["se"] = np.sqrt(s["wv"]) / s["n_played"]
    s["log_rr"] = np.log((s["n_played"] / s["n_held"]) / rate_all_w)
    s = s.drop(columns=["wd", "wv"])
    s.columns = [f"{c}_{name}" for c in s.columns]
    return s

E = window(*args.early, "early")
L = window(*args.late, "late")
M = E.join(L, how="outer")

# 7. k ---------------------------------------------------------------------
ok = M[(M["n_played_early"] >= args.min_plays) & (M["n_played_late"] >= args.min_plays)]
deltas = np.concatenate([ok["rel_delta_early"], ok["rel_delta_late"]])
lrrs = np.concatenate([ok["log_rr_early"], ok["log_rr_late"]])
k_auto = float(np.nanstd(deltas) / np.nanstd(lrrs))
k = args.k if args.k is not None else k_auto
print(f"k auto = {k_auto:.3f} (sd rel_delta {np.nanstd(deltas):.3f} / sd log_rr {np.nanstd(lrrs):.3f}); using k = {k:.3f}")

# 8. scores + quadrants ---------------------------------------------------
for w in ("early", "late"):
    M[f"score_{w}"] = M[f"rel_delta_{w}"] + k * M[f"log_rr_{w}"]
    M[f"z_delta_{w}"] = M[f"rel_delta_{w}"] / M[f"se_{w}"]
cg["score"] = cg["rel_delta"] + k * cg["log_rr"]

def quad(r):
    if not (r["n_played_early"] >= args.min_plays and r["n_played_late"] >= args.min_plays):
        return "insufficient"
    e = "good-early" if r["score_early"] > 0 else "bad-early"
    l = "good-late" if r["score_late"] > 0 else "bad-late"
    return f"{e}/{l}"

M["quadrant"] = M.apply(quad, axis=1)
M = M.reset_index().rename(columns={"index": "Card"})
M = M[["Card", "quadrant", "n_held_early", "n_played_early", "rel_delta_early", "se_early",
       "z_delta_early", "log_rr_early", "score_early",
       "n_held_late", "n_played_late", "rel_delta_late", "se_late", "z_delta_late",
       "log_rr_late", "score_late"]].sort_values("Card")

# 9. outputs ---------------------------------------------------------------
cg_out = cg[["Card", "g", "n_held", "n_played", "rate", "rate_all", "played_mean", "played_all",
             "rel_delta", "se", "log_rr", "score"]].rename(columns={"g": "Gen"})
cg_out.to_csv(out / "card_timing_gen.csv", index=False, float_format="%.4f")
M.to_csv(out / "card_timing_matrix.csv", index=False, float_format="%.4f")
allg.to_csv(out / "card_timing_allgen.csv", index=False, float_format="%.4f")
print(f"wrote {out / 'card_timing_gen.csv'}, {out / 'card_timing_matrix.csv'}")

print("\nAll-card baselines by generation:")
print(allg.assign(rate_all=allg.rate_all.round(3), played_all=allg.played_all.round(3))
      .to_string(index=False))
print(f"\nwindows: early {args.early}, late {args.late}, min plays per window {args.min_plays}")
print("\nQuadrant counts:")
print(M["quadrant"].value_counts().to_string())
fmt = lambda x: f"{x:+.2f}"
for q in ["good-early/bad-late", "bad-early/good-late", "good-early/good-late", "bad-early/bad-late"]:
    sub = M[M.quadrant == q].copy()
    sub["mag"] = sub["score_early"].abs() + sub["score_late"].abs()
    sub = sub.sort_values("mag", ascending=False).head(10)
    print(f"\n{q}  (top 10 by |score_early|+|score_late|)")
    print(sub[["Card", "score_early", "rel_delta_early", "log_rr_early",
               "score_late", "rel_delta_late", "log_rr_late", "n_played_early", "n_played_late"]]
          .to_string(index=False, float_format=fmt))
