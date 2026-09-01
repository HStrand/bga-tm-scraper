"""Corp-stratified elo delta for all cards played in gens LO..HI (standard filters)."""
import sys
from pathlib import Path
import duckdb

lo, hi = int(sys.argv[1]), int(sys.argv[2])
d = (Path(__file__).parent / "db_dump").as_posix()
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
played AS (
  SELECT gc.Card, p.Corporation, COUNT(*) n, AVG(p.Elo) avg_played, STDDEV(p.Elo)/SQRT(COUNT(*)) se_played, SUM(p.Elo) s
  FROM (SELECT DISTINCT TableId, PlayerId, Card FROM '{d}/gamecards.parquet' WHERE PlayedGen BETWEEN {lo} AND {hi}) gc
  JOIN players p USING (TableId, PlayerId) GROUP BY 1,2),
strata AS (
  SELECT pl.Card, pl.Corporation, pl.n, pl.avg_played - (ct.s-pl.s)/(ct.n-pl.n) AS delta, pl.se_played
  FROM played pl JOIN corp_tot ct USING (Corporation) WHERE pl.n>=20 AND ct.n-pl.n>=20)
SELECT Card, SUM(n) AS Played, SUM(n*delta)/SUM(n) AS Delta,
       SQRT(SUM(n*n*se_played*se_played))/SUM(n) AS SE
FROM strata GROUP BY Card HAVING SUM(n)>=200 ORDER BY Delta DESC LIMIT 25
"""
df = duckdb.sql(q).df()
print(df.to_string(index=False, float_format=lambda x: f"{x:+.3f}"))
