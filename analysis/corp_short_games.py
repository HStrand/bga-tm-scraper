"""Per-corp win rate in short (<=cutoff gen) vs long (>=10 gen) games, standard filters, 2p, non-conceded."""
from pathlib import Path
import duckdb, sys
CUTOFF = int(sys.argv[1]) if len(sys.argv)>1 else 9

d = (Path(__file__).parent / "db_dump").as_posix()
q = f"""
WITH ft AS (
  SELECT DISTINCT g.TableId, gs.Generations, gs.Winner
  FROM '{d}/games.parquet' g JOIN '{d}/gamestats.parquet' gs USING (TableId)
  WHERE g.ColoniesOn=FALSE AND g.PreludeOn=TRUE AND g.CorporateEraOn=TRUE
    AND g.GameMode<>'Friendly mode' AND g.Map<>'Amazonis Planitia' AND gs.PlayerCount=2
    AND gs.Conceded=FALSE AND gs.Winner IS NOT NULL AND gs.Generations IS NOT NULL),
players AS (
  SELECT gp.TableId, gp.PlayerId, gps.Corporation,
         CASE WHEN gp.PlayerId=ft.Winner THEN 1.0 ELSE 0.0 END AS Win,
         ft.Generations <= {CUTOFF} AS Short
  FROM '{d}/gameplayers_canonical.parquet' gp JOIN ft USING (TableId)
  JOIN (SELECT DISTINCT TableId, PlayerId, Corporation FROM '{d}/gameplayerstats.parquet') gps
    ON gps.TableId=gp.TableId AND gps.PlayerId=gp.PlayerId)
SELECT Corporation,
  COUNT(*) FILTER (WHERE Short) AS ShortN, AVG(Win) FILTER (WHERE Short) AS ShortWR,
  COUNT(*) FILTER (WHERE NOT Short) AS LongN, AVG(Win) FILTER (WHERE NOT Short) AS LongWR
FROM players GROUP BY 1 HAVING COUNT(*) FILTER (WHERE Short) >= 30 AND COUNT(*) FILTER (WHERE NOT Short) >= 30
"""
df = duckdb.sql(q).df()
df["Diff"] = df.ShortWR - df.LongWR
df["SE"] = ((df.ShortWR*(1-df.ShortWR)/df.ShortN) + (df.LongWR*(1-df.LongWR)/df.LongN))**0.5
df = df.sort_values("Diff", ascending=False)
for c in ["ShortWR","LongWR","Diff","SE"]: df[c] = (df[c]*100).round(1)
print(df.to_string(index=False))
