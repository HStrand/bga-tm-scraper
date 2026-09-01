#!/usr/bin/env python3
"""Precompute a per-(TableId, PlayerId) starting-hand strength covariate.

HandStrength = sum over the player's ENTIRE optioned starting hand -- all offered
corps (2), preludes (4) and project cards (~10), both kept AND not-kept -- of each
item's standalone strength. An item's strength is its pooled mean raw EloChange
over the player-games where that item was KEPT (corp-agnostic; this is a control
covariate, not a causal value, so the keep-cohort mean is exactly the "how well do
hands containing this item tend to do" proxy we want). The covariate is summed over
the OPTIONED set (kept or declined) because the offered menu is fixed before any
keep/play decision -- it is pre-treatment and exogenous.

Outputs (in db_dump/):
  handstrength.parquet  (TableId, PlayerId, HS_corp, HS_prelude, HS_project_total,
                         HandStrength)
  item_values.parquet   (ItemType, Item, value, n)  -- used by the per-card
                         estimator for leave-one-out subtraction.

Standard 2p filters. Usage: python build_handstrength.py
"""

import json
from pathlib import Path

import duckdb

here = Path(__file__).parent
data_dir = here / "db_dump"
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
gameplayers = (data_dir / "gameplayers_canonical.parquet").as_posix()
gameplayerstats = (data_dir / "gameplayerstats.parquet").as_posix()
sh_corp = (data_dir / "startinghandcorporations.parquet").as_posix()
sh_prelude = (data_dir / "startinghandpreludes.parquet").as_posix()
sh_card = (data_dir / "startinghandcards.parquet").as_posix()

# startinghandcards should hold only project cards, but exclude corp/prelude names
# defensively (mirrors rank_cards_kept_mle.py).
preludes = set(json.load(open(here / "preludes.json"))["preludes"])
corps = set(r[0] for r in duckdb.sql(
    f"SELECT DISTINCT Corporation FROM '{gameplayerstats}' WHERE Corporation IS NOT NULL"
).fetchall())
exclude = preludes | corps
exclude_sql = ",".join("'" + c.replace("'", "''") + "'" for c in exclude)

con = duckdb.connect()

# One raw EloChange per player-game, under standard filters. gameplayers_canonical
# is one row per (TableId, PlayerId).
con.sql(f"""
CREATE TEMP TABLE pg AS
WITH filtered_tables AS (
    SELECT DISTINCT g.TableId
    FROM '{games}' g
    JOIN '{gamestats}' gs USING (TableId)
    WHERE g.ColoniesOn = FALSE AND g.PreludeOn = TRUE AND g.CorporateEraOn = TRUE
      AND g.GameMode <> 'Friendly mode' AND g.Map <> 'Amazonis Planitia'
      AND gs.PlayerCount = 2
)
SELECT gp.TableId, gp.PlayerId, CAST(gp.EloChange AS DOUBLE) AS EloChange
FROM '{gameplayers}' gp
JOIN filtered_tables ft USING (TableId)
WHERE gp.EloChange IS NOT NULL
""")

# Per-item strength = mean EloChange over player-games where the item was kept.
con.sql(f"""
CREATE TEMP TABLE item_values AS
SELECT 'corp' AS ItemType, kc.Corporation AS Item,
       AVG(pg.EloChange) AS value, COUNT(*) AS n
FROM (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{sh_corp}' WHERE Kept = TRUE) kc
JOIN pg USING (TableId, PlayerId)
GROUP BY kc.Corporation
UNION ALL
SELECT 'prelude' AS ItemType, kp.Prelude AS Item,
       AVG(pg.EloChange) AS value, COUNT(*) AS n
FROM (SELECT DISTINCT TableId, PlayerId, Prelude FROM '{sh_prelude}' WHERE Kept = TRUE) kp
JOIN pg USING (TableId, PlayerId)
GROUP BY kp.Prelude
UNION ALL
SELECT 'project' AS ItemType, kc.Card AS Item,
       AVG(pg.EloChange) AS value, COUNT(*) AS n
FROM (SELECT DISTINCT TableId, PlayerId, Card FROM '{sh_card}'
      WHERE Kept = TRUE AND Card NOT IN ({exclude_sql})) kc
JOIN pg USING (TableId, PlayerId)
GROUP BY kc.Card
""")

# Sum each item's value over the player's OPTIONED hand (kept or not).
con.sql(f"""
CREATE TEMP TABLE handstrength AS
WITH corp_hs AS (
    SELECT o.TableId, o.PlayerId, SUM(iv.value) AS HS_corp
    FROM (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{sh_corp}') o
    JOIN item_values iv ON iv.ItemType = 'corp' AND iv.Item = o.Corporation
    GROUP BY o.TableId, o.PlayerId
),
prelude_hs AS (
    SELECT o.TableId, o.PlayerId, SUM(iv.value) AS HS_prelude
    FROM (SELECT DISTINCT TableId, PlayerId, Prelude FROM '{sh_prelude}') o
    JOIN item_values iv ON iv.ItemType = 'prelude' AND iv.Item = o.Prelude
    GROUP BY o.TableId, o.PlayerId
),
project_hs AS (
    SELECT o.TableId, o.PlayerId, SUM(iv.value) AS HS_project_total
    FROM (SELECT DISTINCT TableId, PlayerId, Card FROM '{sh_card}') o
    JOIN item_values iv ON iv.ItemType = 'project' AND iv.Item = o.Card
    GROUP BY o.TableId, o.PlayerId
)
SELECT pg.TableId, pg.PlayerId,
       COALESCE(c.HS_corp, 0.0) AS HS_corp,
       COALESCE(p.HS_prelude, 0.0) AS HS_prelude,
       COALESCE(j.HS_project_total, 0.0) AS HS_project_total,
       COALESCE(c.HS_corp, 0.0) + COALESCE(p.HS_prelude, 0.0)
           + COALESCE(j.HS_project_total, 0.0) AS HandStrength
FROM pg
LEFT JOIN corp_hs c USING (TableId, PlayerId)
LEFT JOIN prelude_hs p USING (TableId, PlayerId)
LEFT JOIN project_hs j USING (TableId, PlayerId)
""")

hs_out = (data_dir / "handstrength.parquet").as_posix()
iv_out = (data_dir / "item_values.parquet").as_posix()
con.sql(f"COPY handstrength TO '{hs_out}' (FORMAT PARQUET)")
con.sql(f"COPY item_values TO '{iv_out}' (FORMAT PARQUET)")

n_rows = con.sql("SELECT COUNT(*) FROM handstrength").fetchone()[0]
summary = con.sql("""
SELECT COUNT(*) AS player_games,
       AVG(HandStrength) AS mean_hs, STDDEV(HandStrength) AS sd_hs,
       MIN(HandStrength) AS min_hs, MAX(HandStrength) AS max_hs
FROM handstrength
""").df()
counts = con.sql("""
SELECT ItemType, COUNT(*) AS items, MIN(n) AS min_n, MAX(n) AS max_n
FROM item_values GROUP BY ItemType ORDER BY ItemType
""").df()

print(f"Wrote {hs_out} ({n_rows} player-games)")
print(f"Wrote {iv_out}")
print("\nHandStrength distribution:")
print(summary.to_string(index=False))
print("\nItem value tables:")
print(counts.to_string(index=False))
