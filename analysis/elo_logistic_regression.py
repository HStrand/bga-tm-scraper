#!/usr/bin/env python3
"""
Find the optimal Elo scale factor for BGA Terraforming Mars.

The standard Elo expected-score formula is:
    P(A wins) = 1 / (1 + 10^((R_B - R_A) / scale))

In chess scale=400. We find the optimal scale for this dataset by fitting a
logistic regression on observed 2-player game outcomes. Since the Elo formula is
a sigmoid, fitting P = sigmoid(β * elo_diff) with no intercept gives
scale = ln(10)/β.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression

# ── Data pipeline ──────────────────────────────────────────────────────────

df = pd.read_csv("db_dump/gameplayers.csv", encoding="utf-8-sig")

# Drop rows where Elo is missing
df = df.dropna(subset=["Elo"])
df["Elo"] = pd.to_numeric(df["Elo"])

# Deduplicate: for TableIds scraped from multiple perspectives, keep only one
# Pick one perspective per TableId, then keep all player rows for that perspective
first_perspective = df.groupby("TableId")["PlayerPerspective"].first().reset_index()
first_perspective.columns = ["TableId", "_keep_perspective"]
df = df.merge(first_perspective, on="TableId")
df = df[df["PlayerPerspective"] == df["_keep_perspective"]].drop(columns="_keep_perspective")

# Filter to 2-player games only
players_per_game = df.groupby("TableId").size()
two_player_tables = players_per_game[players_per_game == 2].index
df = df[df["TableId"].isin(two_player_tables)]

# Group into pairs and determine winner using Position (1 = winner)
# Data is sorted by Position, so rows are [winner, loser].
# Randomly assign "Player A" role to avoid ordering bias.
games = df.groupby("TableId").agg(list)

rng = np.random.default_rng(42)
xs = []
ys = []
for _, row in games.iterrows():
    elos = row["Elo"]
    positions = row["Position"]

    # Skip ties (both same position)
    if positions[0] == positions[1]:
        continue

    winner_elo = elos[0]  # Position 1
    loser_elo = elos[1]   # Position 2

    # Randomly assign which player is "A"
    if rng.random() < 0.5:
        elo_diff = winner_elo - loser_elo
        a_won = 1
    else:
        elo_diff = loser_elo - winner_elo
        a_won = 0

    xs.append(elo_diff)
    ys.append(a_won)

X = np.array(xs).reshape(-1, 1)
y = np.array(ys)

print(f"Games analyzed: {len(y):,}")
print(f"Elo diff range: [{X.min():.0f}, {X.max():.0f}]")

higher_rated_wins = np.mean(y[X.ravel() > 0])
print(f"Win rate for higher-rated player: {higher_rated_wins:.1%}")

# ── Logistic regression ───────────────────────────────────────────────────

# Primary model: no intercept, no regularization (pure MLE)
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

# ── Visualization ─────────────────────────────────────────────────────────

# Bin empirical win rates
n_bins = 25
bin_edges = np.linspace(X.min(), X.max(), n_bins + 1)
bin_centers = []
bin_win_rates = []
bin_counts = []

for i in range(n_bins):
    mask = (X.ravel() >= bin_edges[i]) & (X.ravel() < bin_edges[i + 1])
    count = mask.sum()
    if count < 10:
        continue
    bin_centers.append((bin_edges[i] + bin_edges[i + 1]) / 2)
    bin_win_rates.append(y[mask].mean())
    bin_counts.append(count)

bin_centers = np.array(bin_centers)
bin_win_rates = np.array(bin_win_rates)
bin_counts = np.array(bin_counts)

# Curves
x_curve = np.linspace(X.min(), X.max(), 500)
y_fitted = 1 / (1 + 10 ** (-x_curve / scale_optimal))
y_chess = 1 / (1 + 10 ** (-x_curve / 400))

fig, ax = plt.subplots(figsize=(10, 6))

# Empirical points (size proportional to sample count)
sizes = 20 + 200 * (bin_counts / bin_counts.max())
ax.scatter(bin_centers, bin_win_rates, s=sizes, c="steelblue", alpha=0.7,
           edgecolors="navy", zorder=3, label="Empirical win rate")

# Fitted curve
ax.plot(x_curve, y_fitted, color="red", linewidth=2,
        label=f"Fitted (scale={scale_optimal:.0f})")

# Chess reference
ax.plot(x_curve, y_chess, color="gray", linewidth=1.5, linestyle="--",
        label="Chess standard (scale=400)")

# Reference lines
ax.axhline(0.5, color="lightgray", linewidth=0.8, zorder=1)
ax.axvline(0, color="lightgray", linewidth=0.8, zorder=1)

ax.set_xlabel("Elo Difference (Player A − Player B)")
ax.set_ylabel("P(Player A wins)")
ax.set_title("Elo Logistic Regression - BGA Terraforming Mars (2-player)")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
plt.show()
