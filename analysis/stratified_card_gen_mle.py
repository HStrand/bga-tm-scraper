#!/usr/bin/env python3
"""Corp-stratified MLE-residual delta for playing a card in a given gen (standard filters).

Same design as stratified_card_gen_elo.py, but replaces BGA's EloChange with a
calibrated per-game residual:

    PreElo = Elo - EloChange            (pre-game rating, matched pair per row)
    E      = 1 / (1 + 10^((PreElo_opp - PreElo_self) / S_FACTOR))
    R      = ActualScore - E            (ActualScore = 1 win / 0 loss)

This is EloChange recomputed with a constant K (=1) and the correct logistic
slope S_FACTOR=310, removing BGA's variable provisional-K weighting ("upset
bias") and its s=400 miscalibration. Residual R is in win-probability units
(~-1..1); set --scale to express it in Elo-like points (rankings are unchanged
by the scale, it's a constant multiplier).

Within each corporation, compares played-in-gen vs not-played, then averages
the per-corp deltas weighted by the played-cohort size.

Usage: python stratified_card_gen_mle.py "Card Name" [gen] [--scale K]
"""

import math
import sys
from pathlib import Path

import duckdb

S_FACTOR = 310.0

argv = [a for a in sys.argv[1:]]
scale = 20.0  # BGA's standard display K; pure cosmetic multiplier, does not affect rankings
if "--scale" in argv:
    i = argv.index("--scale")
    scale = float(argv[i + 1])
    del argv[i:i + 2]

card = argv[0]
gen = int(argv[1]) if len(argv) > 1 else 1
card_sql = card.replace("'", "''")

here = Path(__file__).parent
data_dir = here / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (data_dir / "gameplayerstats.parquet").as_posix()

query = f"""
WITH filtered_tables AS (
    SELECT DISTINCT g.TableId
    FROM '{games}' g
    JOIN '{gamestats}' gs USING (TableId)
    WHERE g.ColoniesOn = FALSE
      AND g.PreludeOn = TRUE
      AND g.CorporateEraOn = TRUE
      AND g.GameMode <> 'Friendly mode'
      AND g.Map <> 'Amazonis Planitia'
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
    -- 2p table: opponent is the other player in the same TableId
    SELECT b.TableId, b.PlayerId,
           {scale} * (b.ActualScore
               - 1.0 / (1.0 + pow(10.0, (o.PreElo - b.PreElo) / {S_FACTOR}))) AS R
    FROM base b
    JOIN base o ON o.TableId = b.TableId AND o.PlayerId <> b.PlayerId
),
players AS (
    SELECT r.TableId, r.PlayerId, r.R, gps.Corporation,
           EXISTS (
               SELECT 1 FROM '{gamecards}' gc
               WHERE gc.TableId = r.TableId AND gc.PlayerId = r.PlayerId
                 AND gc.Card = '{card_sql}' AND gc.PlayedGen = {gen}
           ) AS PlayedInGen
    FROM resid r
    JOIN (
        SELECT DISTINCT TableId, PlayerId, Corporation FROM '{gameplayerstats}'
    ) gps ON gps.TableId = r.TableId AND gps.PlayerId = r.PlayerId
)
SELECT Corporation,
       COUNT(*) FILTER (WHERE PlayedInGen) AS PlayedGames,
       AVG(R) FILTER (WHERE PlayedInGen) AS PlayedAvg,
       STDDEV(R) FILTER (WHERE PlayedInGen)
           / SQRT(COUNT(*) FILTER (WHERE PlayedInGen)) AS PlayedSE,
       COUNT(*) FILTER (WHERE NOT PlayedInGen) AS ControlGames,
       AVG(R) FILTER (WHERE NOT PlayedInGen) AS ControlAvg,
       STDDEV(R) FILTER (WHERE NOT PlayedInGen)
           / SQRT(COUNT(*) FILTER (WHERE NOT PlayedInGen)) AS ControlSE
FROM players
GROUP BY Corporation
HAVING COUNT(*) FILTER (WHERE PlayedInGen) >= 20
ORDER BY PlayedGames DESC
"""

df = duckdb.sql(query).df()
df["Delta"] = df["PlayedAvg"] - df["ControlAvg"]
df["DeltaSE"] = (df["PlayedSE"] ** 2 + df["ControlSE"] ** 2) ** 0.5

w = df["PlayedGames"]
total = float((w * df["Delta"]).sum() / w.sum())
total_se = math.sqrt(float((w**2 * df["DeltaSE"] ** 2).sum())) / float(w.sum())

cols = ["Corporation", "PlayedGames", "PlayedAvg", "ControlAvg", "Delta", "DeltaSE"]
print(df[cols].to_string(index=False))
unit = "elo-pts" if scale != 1.0 else "win-prob"
print(f"\n{card} gen {gen}: stratified MLE-residual delta = {total:+.4f} +/- {total_se:.4f} "
      f"[{unit}, s={S_FACTOR:.0f}, scale={scale:g}] "
      f"({int(w.sum())} played games across {len(df)} corps)")
