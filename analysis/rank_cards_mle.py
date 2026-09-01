#!/usr/bin/env python3
"""Rank project cards by corp-stratified MLE-residual delta (standard filters).

Same estimator as stratified_card_gen_mle.py, computed set-based for every
project card at once: played-the-card (any gen) vs did-not, stratified within
corporation, deltas weighted by played-cohort size.

Project cards = cards in gamecards excluding corporations and preludes.
Per-corp cohorts require >= MIN_CORP_N played games; cards require >= MIN_TOTAL
played games across qualifying corps to be ranked.

Residual R = scale * (ActualScore - 1/(1+10^((PreElo_opp-PreElo_self)/310))),
scale=20 (BGA display K, cosmetic only).

Usage: python rank_cards_mle.py [top_n] [--min-total N] [--min-corp N]
"""

import json
import sys
from pathlib import Path

import duckdb

S_FACTOR = 310.0
SCALE = 20.0
MIN_CORP_N = 20
MIN_TOTAL = 500

argv = sys.argv[1:]
if "--min-total" in argv:
    i = argv.index("--min-total"); MIN_TOTAL = int(argv[i + 1]); del argv[i:i + 2]
if "--min-corp" in argv:
    i = argv.index("--min-corp"); MIN_CORP_N = int(argv[i + 1]); del argv[i:i + 2]
top_n = int(argv[0]) if argv else 20

here = Path(__file__).parent
data_dir = here / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (data_dir / "gameplayerstats.parquet").as_posix()

preludes = set(json.load(open(here / "preludes.json"))["preludes"])
corps = set(r[0] for r in duckdb.sql(
    f"SELECT DISTINCT Corporation FROM '{gameplayerstats}' WHERE Corporation IS NOT NULL"
).fetchall())
exclude = preludes | corps
exclude_sql = ",".join("'" + c.replace("'", "''") + "'" for c in exclude)

query = f"""
WITH filtered_tables AS (
    SELECT DISTINCT g.TableId
    FROM '{games}' g
    JOIN '{gamestats}' gs USING (TableId)
    WHERE g.ColoniesOn = FALSE AND g.PreludeOn = TRUE AND g.CorporateEraOn = TRUE
      AND g.GameMode <> 'Friendly mode' AND g.Map <> 'Amazonis Planitia'
      AND gs.PlayerCount = 2
),
base AS (
    SELECT gp.TableId, gp.PlayerId,
           CAST(gp.Elo - gp.EloChange AS DOUBLE) AS PreElo,
           CASE WHEN gp.Position = 1 THEN 1.0 ELSE 0.0 END AS ActualScore
    FROM '{gameplayers}' gp
    JOIN filtered_tables ft USING (TableId)
    WHERE gp.EloChange IS NOT NULL AND gp.Elo IS NOT NULL
),
resid AS (
    SELECT b.TableId, b.PlayerId,
           {SCALE} * (b.ActualScore
               - 1.0 / (1.0 + pow(10.0, (o.PreElo - b.PreElo) / {S_FACTOR}))) AS R
    FROM base b
    JOIN base o ON o.TableId = b.TableId AND o.PlayerId <> b.PlayerId
),
pg AS (  -- one residual per player-game, with corp
    SELECT r.TableId, r.PlayerId, r.R, gps.Corporation
    FROM resid r
    JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gameplayerstats}') gps
      ON gps.TableId = r.TableId AND gps.PlayerId = r.PlayerId
    WHERE gps.Corporation IS NOT NULL
),
corp_tot AS (
    SELECT Corporation, COUNT(*) n, SUM(R) s, SUM(R*R) ss
    FROM pg GROUP BY Corporation
),
played AS (  -- player-games where the card was actually played, by card+corp
    SELECT pc.Card, pg.Corporation,
           COUNT(*) n, SUM(pg.R) s, SUM(pg.R*pg.R) ss
    FROM pg
    JOIN (SELECT DISTINCT TableId, PlayerId, Card FROM '{gamecards}'
          WHERE PlayedGen IS NOT NULL AND Card NOT IN ({exclude_sql})) pc
      ON pc.TableId = pg.TableId AND pc.PlayerId = pg.PlayerId
    GROUP BY pc.Card, pg.Corporation
)
SELECT p.Card, p.Corporation,
       p.n AS played_n, p.s AS played_s, p.ss AS played_ss,
       (t.n - p.n) AS ctrl_n, (t.s - p.s) AS ctrl_s, (t.ss - p.ss) AS ctrl_ss
FROM played p JOIN corp_tot t USING (Corporation)
WHERE p.n >= {MIN_CORP_N} AND (t.n - p.n) >= {MIN_CORP_N}
"""

df = duckdb.sql(query).df()


def stats(n, s, ss):
    mean = s / n
    var = (ss - s * s / n) / (n - 1)
    return mean, (var / n) ** 0.5  # mean, SE


rows = []
for card, g in df.groupby("Card"):
    pm, pse = [], []
    w = []
    for _, r in g.iterrows():
        pmean, pse_ = stats(r.played_n, r.played_s, r.played_ss)
        cmean, cse_ = stats(r.ctrl_n, r.ctrl_s, r.ctrl_ss)
        delta = pmean - cmean
        dse = (pse_ ** 2 + cse_ ** 2) ** 0.5
        pm.append(delta); pse.append(dse); w.append(r.played_n)
    W = sum(w)
    if W < MIN_TOTAL:
        continue
    total = sum(wi * di for wi, di in zip(w, pm)) / W
    total_se = (sum((wi ** 2) * (se ** 2) for wi, se in zip(w, pse))) ** 0.5 / W
    rows.append((card, total, total_se, int(W), len(g)))

rows.sort(key=lambda x: x[1], reverse=True)
n_qualified = len(rows)

print(f"Project cards ranked by stratified MLE-residual delta (elo-pts, s={S_FACTOR:.0f}, "
      f"scale={SCALE:g}); 2p standard filters.")
print(f"Thresholds: per-corp >= {MIN_CORP_N} played, total >= {MIN_TOTAL} played. "
      f"{n_qualified} cards qualified.\n")
print(f"{'#':>3}  {'Card':<32}{'delta':>9}{'+/-SE':>8}{'t':>7}{'played':>9}{'corps':>7}")
for i, (card, total, se, W, nc) in enumerate(rows[:top_n], 1):
    t = total / se if se else 0.0
    print(f"{i:>3}  {card:<32}{total:>+9.3f}{se:>8.3f}{t:>7.1f}{W:>9}{nc:>7}")
