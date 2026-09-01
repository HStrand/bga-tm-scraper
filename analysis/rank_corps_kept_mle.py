#!/usr/bin/env python3
"""Rank corporations by MLE-residual delta when KEPT from the starting hand
(standard filters).

Companion to rank_cards_kept_mle.py. The corp kept from the opening selection
(startinghandcorporations.Kept = TRUE) is the corp the player plays, so each
player-game contributes to exactly one corp. Unlike the card rankings, there is
NO corp-stratification here -- the corporation IS the treatment, so there is
nothing to stratify on. The residual already adjusts for opponent rating, so the
per-corp mean residual is corp strength controlling for rating; delta compares a
corp against all other corps pooled.

Residual R = scale * (ActualScore - 1/(1+10^((PreElo_opp-PreElo_self)/310))),
scale=20 (BGA display K, cosmetic only).

Usage: python rank_corps_kept_mle.py [--min-total N]
"""

import sys
from pathlib import Path

import duckdb

S_FACTOR = 310.0
SCALE = 20.0
MIN_TOTAL = 100

argv = sys.argv[1:]
if "--min-total" in argv:
    i = argv.index("--min-total"); MIN_TOTAL = int(argv[i + 1]); del argv[i:i + 2]

here = Path(__file__).parent
data_dir = here / "db_dump"
startingcorp = (data_dir / "startinghandcorporations.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()

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
pg AS (  -- one residual per player-game, tagged with the kept (played) corp
    SELECT r.R, kc.Corporation
    FROM resid r
    JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{startingcorp}'
          WHERE Kept = TRUE) kc
      ON kc.TableId = r.TableId AND kc.PlayerId = r.PlayerId
    WHERE kc.Corporation IS NOT NULL
)
SELECT Corporation, COUNT(*) n, SUM(R) s, SUM(R*R) ss FROM pg GROUP BY Corporation
"""

df = duckdb.sql(query).df()
N = float(df["n"].sum()); S = float(df["s"].sum()); SS = float(df["ss"].sum())


def stats(n, s, ss):
    mean = s / n
    var = (ss - s * s / n) / (n - 1)
    return mean, (var / n) ** 0.5


rows = []
for _, r in df.iterrows():
    if r.n < MIN_TOTAL:
        continue
    pmean, pse = stats(r.n, r.s, r.ss)
    cmean, cse = stats(N - r.n, S - r.s, SS - r.ss)
    delta = pmean - cmean
    dse = (pse ** 2 + cse ** 2) ** 0.5
    rows.append((r.Corporation, delta, dse, pmean, int(r.n)))

rows.sort(key=lambda x: x[1], reverse=True)

print(f"Corporations ranked by MLE-residual delta when kept from starting hand "
      f"(elo-pts, s={S_FACTOR:.0f}, scale={SCALE:g}); 2p standard filters. "
      f"No corp-stratification (corp is the treatment).")
print(f"delta = corp mean residual - all-other-corps mean. {len(rows)} corps "
      f"(>= {MIN_TOTAL} games).\n")
print(f"{'#':>3}  {'Corporation':<32}{'delta':>9}{'+/-SE':>8}{'t':>7}{'meanR':>9}{'games':>9}")
for i, (corp, delta, se, meanR, n) in enumerate(rows, 1):
    t = delta / se if se else 0.0
    print(f"{i:>3}  {corp:<32}{delta:>+9.3f}{se:>8.3f}{t:>7.1f}{meanR:>+9.3f}{n:>9}")
