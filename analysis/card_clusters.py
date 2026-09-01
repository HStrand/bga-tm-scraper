#!/usr/bin/env python3
"""Cluster TM cards by co-play patterns (same player, same game) into K=6 clusters."""

import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

K = 6
RANDOM_STATE = 42

PRELUDE_CARDS = [
    "Acquired Space Agency", "Allied Bank", "Allied Banks", "Aquifer Turbines",
    "Biofuels", "Biolabs", "Biosphere Support", "Business Empire",
    "Dome Farming", "Donation", "Early Settlement", "Eccentric Sponsor",
    "Ecology Experts", "Excentric Sponsor", "Experimental Forest",
    "Galilean Mining", "Great Aquifer", "Huge Asteroid", "Io Research Outpost",
    "Loan", "Martian Industries", "Metal-Rich Asteroid", "Metals Company",
    "Mining Operations", "Mohole", "Mohole Excavation", "Nitrogen Shipment",
    "Orbital Construction Yard", "Polar Industries", "Power Generation",
    "Research Network", "Self-Sufficient Settlement", "Smelting Plant",
    "Society Support", "Supplier", "Supply Drop", "UNMI Contractor",
]
PRELUDE_SQL_LIST = ", ".join(f"'{c.replace(chr(39), chr(39)*2)}'" for c in PRELUDE_CARDS)

data_dir = Path(__file__).parent / "db_dump"
gamecards = (data_dir / "gamecards.parquet").as_posix()
games = (data_dir / "games.parquet").as_posix()
gamestats = (data_dir / "gamestats.parquet").as_posix()
out_csv = Path(__file__).parent / "card_clusters.csv"
out_png = Path(__file__).parent / "card_clusters.png"

query = f"""
WITH filtered_tables AS (
    SELECT g.TableId
    FROM '{games}' g
    JOIN '{gamestats}' gs USING (TableId)
    WHERE g.ColoniesOn = FALSE
      AND g.PreludeOn = TRUE
      AND g.CorporateEraOn = TRUE
      AND g.GameMode <> 'Friendly mode'
      AND g.Map <> 'Amazonis Planitia'
      AND gs.PlayerCount = 2
)
SELECT gc.TableId, gc.PlayerId, gc.Card
FROM '{gamecards}' gc
JOIN filtered_tables ft USING (TableId)
WHERE gc.PlayedGen IS NOT NULL
  AND NOT regexp_matches(gc.Card, '^card[ _]')
  AND gc.Card NOT IN ({PRELUDE_SQL_LIST})
"""

t0 = time.perf_counter()
df = duckdb.sql(query).df()
print(f"DuckDB pull: {time.perf_counter() - t0:.2f}s — {len(df):,} played-card rows")

pg_ids, pg_index = np.unique(
    df[["TableId", "PlayerId"]].to_records(index=False), return_inverse=True
)
cards, card_index = np.unique(df["Card"].to_numpy(), return_inverse=True)
n_pg = len(pg_ids)
n_cards = len(cards)
print(f"Player-games: {n_pg:,}  |  Unique cards: {n_cards}")

X = csr_matrix(
    (np.ones(len(df), dtype=np.float32), (pg_index, card_index)),
    shape=(n_pg, n_cards),
)
X.data = np.ones_like(X.data)

play_counts = np.asarray(X.sum(axis=0)).ravel().astype(np.int64)

M = (X.T @ X).toarray().astype(np.float64)
np.fill_diagonal(M, 0.0)

M_norm = normalize(M, norm="l2", axis=1)

km = KMeans(n_clusters=K, n_init=10, random_state=RANDOM_STATE)
labels = km.fit_predict(M_norm)

out = pd.DataFrame({"Card": cards, "ClusterId": labels, "PlayCount": play_counts})
out = out.sort_values(["ClusterId", "PlayCount"], ascending=[True, False]).reset_index(drop=True)
out.to_csv(out_csv, index=False)
print(f"\nWrote {out_csv}  ({len(out)} cards)\n")

for cid in range(K):
    sub = out[out["ClusterId"] == cid]
    print(f"Cluster {cid}  —  {len(sub)} cards")
    print(sub.head(10)[["Card", "PlayCount"]].to_string(index=False))
    print()

coords = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(M_norm)
fig, ax = plt.subplots(figsize=(13, 9))
cmap = plt.get_cmap("tab10")
for cid in range(K):
    mask = labels == cid
    ax.scatter(coords[mask, 0], coords[mask, 1], s=28, color=cmap(cid),
               label=f"Cluster {cid} (n={int(mask.sum())})", alpha=0.75, edgecolor="white", linewidth=0.4)

for cid in range(K):
    mask = labels == cid
    top_idx = np.argsort(play_counts[mask])[::-1][:3]
    cluster_cards = cards[mask]
    cluster_coords = coords[mask]
    for i in top_idx:
        ax.annotate(cluster_cards[i], (cluster_coords[i, 0], cluster_coords[i, 1]),
                    fontsize=7, alpha=0.85, xytext=(3, 3), textcoords="offset points")

ax.set_title(f"TM card clusters — KMeans (k={K}) on L2-normalized co-play")
ax.set_xlabel("PC1")
ax.set_ylabel("PC2")
ax.legend(loc="best", fontsize=9, framealpha=0.9)
ax.grid(True, alpha=0.25)
fig.tight_layout()
fig.savefig(out_png, dpi=140)
print(f"Wrote {out_png}")
