"""Corp-stratified elo delta per phase (opening 1-4, middlegame 5-8, endgame 9-12) for given cards."""
import sys
from pathlib import Path
import duckdb, pandas as pd

cards = sys.argv[1:]
PH = [("Opening",1,4),("Middlegame",5,8),("Endgame",9,12)]
d = (Path(__file__).parent / "db_dump").as_posix()
cl = ",".join("'"+c.replace("'","''")+"'" for c in cards)
q = f"""
WITH ft AS (
  SELECT DISTINCT g.TableId FROM '{d}/games.parquet' g JOIN '{d}/gamestats.parquet' gs USING (TableId)
  WHERE g.ColoniesOn=FALSE AND g.PreludeOn=TRUE AND g.CorporateEraOn=TRUE
    AND g.GameMode<>'Friendly mode' AND g.Map<>'Amazonis Planitia' AND gs.PlayerCount=2),
players AS (
  SELECT gp.TableId, gp.PlayerId, CAST(gp.EloChange AS DOUBLE) AS Elo, gps.Corporation
  FROM '{d}/gameplayers_canonical.parquet' gp JOIN ft USING (TableId)
  JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{d}/gameplayerstats.parquet') gps
    ON gps.TableId=gp.TableId AND gps.PlayerId=gp.PlayerId
  WHERE gp.EloChange IS NOT NULL),
corp_tot AS (SELECT Corporation, COUNT(*) n, SUM(Elo) s FROM players GROUP BY 1),
ph AS (SELECT * FROM (VALUES {",".join(f"('{n}',{a},{b})" for n,a,b in PH)}) t(Phase,lo,hi)),
played AS (
  SELECT gc.Card, ph.Phase, p.Corporation, COUNT(*) n, AVG(p.Elo) avg_played, STDDEV(p.Elo)/SQRT(COUNT(*)) se_played, SUM(p.Elo) s
  FROM (SELECT DISTINCT TableId, PlayerId, Card, MIN(PlayedGen) g FROM '{d}/gamecards.parquet' WHERE Card IN ({cl}) GROUP BY 1,2,3) gc
  JOIN ph ON gc.g BETWEEN ph.lo AND ph.hi
  JOIN players p USING (TableId, PlayerId) GROUP BY 1,2,3),
strata AS (
  SELECT pl.Card, pl.Phase, pl.n, pl.avg_played - (ct.s-pl.s)/(ct.n-pl.n) AS delta, pl.se_played
  FROM played pl JOIN corp_tot ct USING (Corporation) WHERE pl.n>=20 AND ct.n-pl.n>=20)
SELECT Card, Phase, SUM(n) AS Played, SUM(n*delta)/SUM(n) AS Delta, SQRT(SUM(n*n*se_played*se_played))/SUM(n) AS SE
FROM strata GROUP BY 1,2
"""
df = duckdb.sql(q).df()
df["cell"] = df.apply(lambda r: f"{r.Delta:+.2f} ({int(r.Played)})", axis=1)
t = df.pivot(index="Card", columns="Phase", values="cell").reindex(index=cards, columns=[p[0] for p in PH])
print(t.to_string())
