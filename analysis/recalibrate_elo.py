#!/usr/bin/env python3
"""
Recalibrate BGA Elo ratings to the standard chess scale.

BGA's Elo system uses a narrower scale (~310) than chess (400). This script:
1. Fits the optimal scale using pairwise comparisons from 2-player and 3-player games
2. Adds a CalibratedEloChange column to gameplayers.csv by recomputing each player's
   expected score with the fitted scale and deriving what the Elo change would have been
"""

import itertools

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

# ── Load CSV ──────────────────────────────────────────────────────────────

csv_path = "db_dump/gameplayers.csv"
df_full = pd.read_csv(csv_path, encoding="utf-8-sig")

# ── Build fitting dataset ─────────────────────────────────────────────────

df = df_full.dropna(subset=["Elo"]).copy()
df["Elo"] = pd.to_numeric(df["Elo"])

# Deduplicate: keep one perspective per TableId
first_perspective = df.groupby("TableId")["PlayerPerspective"].first().reset_index()
first_perspective.columns = ["TableId", "_keep_perspective"]
df = df.merge(first_perspective, on="TableId")
df = df[df["PlayerPerspective"] == df["_keep_perspective"]].drop(columns="_keep_perspective")

# Split by player count
players_per_game = df.groupby("TableId").size()

two_player_tables = players_per_game[players_per_game == 2].index
three_player_tables = players_per_game[players_per_game == 3].index

df_2p = df[df["TableId"].isin(two_player_tables)]
df_3p = df[df["TableId"].isin(three_player_tables)]

print(f"2-player games: {len(two_player_tables):,}")
print(f"3-player games: {len(three_player_tables):,}")

# ── Extract pairwise comparisons ──────────────────────────────────────────

rng = np.random.default_rng(42)
xs = []
ys = []

# 2-player: 1 pair per game
ties_2p = 0
games_2p = df_2p.groupby("TableId").agg(list)
for _, row in games_2p.iterrows():
    elos = row["Elo"]
    positions = row["Position"]

    if positions[0] == positions[1]:
        ties_2p += 1
        continue

    winner_idx = 0 if positions[0] < positions[1] else 1
    loser_idx = 1 - winner_idx
    winner_elo = elos[winner_idx]
    loser_elo = elos[loser_idx]

    if rng.random() < 0.5:
        xs.append(winner_elo - loser_elo)
        ys.append(1)
    else:
        xs.append(loser_elo - winner_elo)
        ys.append(0)

pairs_2p = len(ys)
print(f"2-player pairs: {pairs_2p:,} (ties skipped: {ties_2p})")

# 3-player: 3 pairs per game via combinations
ties_3p = 0
games_3p = df_3p.groupby("TableId").agg(list)
for _, row in games_3p.iterrows():
    elos = row["Elo"]
    positions = row["Position"]

    for i, j in itertools.combinations(range(3), 2):
        if positions[i] == positions[j]:
            ties_3p += 1
            continue

        if positions[i] < positions[j]:
            winner_elo = elos[i]
            loser_elo = elos[j]
        else:
            winner_elo = elos[j]
            loser_elo = elos[i]

        if rng.random() < 0.5:
            xs.append(winner_elo - loser_elo)
            ys.append(1)
        else:
            xs.append(loser_elo - winner_elo)
            ys.append(0)

pairs_3p = len(ys) - pairs_2p
print(f"3-player pairs: {pairs_3p:,} (tied pairs skipped: {ties_3p})")
print(f"Total pairs: {len(ys):,}")

X = np.array(xs).reshape(-1, 1)
y = np.array(ys)

# ── Logistic regression ──────────────────────────────────────────────────

model = LogisticRegression(fit_intercept=False, C=1e10, max_iter=1000)
model.fit(X, y)

beta = model.coef_[0][0]
scale_optimal = np.log(10) / beta

print(f"\nOptimal scale = {scale_optimal:.1f}  (chess standard: 400)")
print(f"  beta = {beta:.6f}")

# Sanity check: with intercept
model_intercept = LogisticRegression(fit_intercept=True, C=1e10, max_iter=1000)
model_intercept.fit(X, y)

print(f"\nSanity check (with intercept):")
print(f"  intercept = {model_intercept.intercept_[0]:.4f}  (should be ~0)")
print(f"  beta = {model_intercept.coef_[0][0]:.6f}")

# ── Compute CalibratedEloChange per row ──────────────────────────────────
# For each player, compute expected score using avg opponent Elo, then:
#   E_bga  = 1 / (1 + 10^((avg_opp - self) / 400))       # what BGA used
#   E_cal  = 1 / (1 + 10^((avg_opp - self) / scale_opt))  # calibrated
#   S      = (N - Position) / (N - 1)                      # actual score
#   CalibratedEloChange = EloChange * (S - E_cal) / (S - E_bga)
# This preserves BGA's K-factor while correcting the expected score.

group_cols = ["TableId", "PlayerPerspective"]

elo_stats = (
    df_full.groupby(group_cols)["Elo"]
    .agg(elo_sum="sum", elo_count="count")
    .reset_index()
)
n_players = df_full.groupby(group_cols).size().reset_index(name="n_players")

df_full = df_full.merge(elo_stats, on=group_cols).merge(n_players, on=group_cols)

avg_opp_elo = (df_full["elo_sum"] - df_full["Elo"]) / (df_full["elo_count"] - 1)
elo_diff = avg_opp_elo - df_full["Elo"]

E_bga = 1 / (1 + 10 ** (elo_diff / 400))
E_cal = 1 / (1 + 10 ** (elo_diff / scale_optimal))
S = (df_full["n_players"] - df_full["Position"]) / (df_full["n_players"] - 1)

# Ratio (S - E_cal) / (S - E_bga); when denominator ≈ 0, EloChange ≈ 0 too
denom = S - E_bga
ratio = np.where(np.abs(denom) < 1e-10, 1.0, (S - E_cal) / denom)

df_full["CalibratedEloChange"] = (df_full["EloChange"] * ratio).round(1)

# Clean up helper columns and any stale columns from previous runs
df_full = df_full.drop(columns=["elo_sum", "elo_count", "n_players"])
df_full = df_full.drop(columns=["CalibratedElo"], errors="ignore")

df_full.to_csv(csv_path, index=False, encoding="utf-8-sig")

print(f"\nSaved CalibratedEloChange to {csv_path}")
print(f"  Rows with CalibratedEloChange: {df_full['CalibratedEloChange'].notna().sum():,}")
print(f"  Rows with NaN: {df_full['CalibratedEloChange'].isna().sum():,}")
