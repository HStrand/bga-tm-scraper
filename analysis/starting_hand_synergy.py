#!/usr/bin/env python3
"""
Analyze starting hand synergy between cards and corporations in Terraforming Mars.

Computes synergy gain for card-corporation combos:
    synergy = combo_avg_elo - (card_baseline_elo + corp_baseline_elo)

A positive synergy means the combo performs better than the sum of its parts.

Usage:
    python analysis/starting_hand_synergy.py "Earth Catapult"
    python analysis/starting_hand_synergy.py "earth cat" --min-games 100
"""

import argparse
import csv
import sys
from difflib import get_close_matches
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_csv_dict(filepath, key_col, value_col, games_col="PlayerGames"):
    """Load a CSV into a dict mapping key_col -> (float(value_col), int(games_col))."""
    result = {}
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            result[row[key_col]] = (float(row[value_col]), int(row[games_col]))
    return result


def load_combo_data(filepath):
    """Load card-corporation combo CSV into a list of dicts."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({
                "corporation": row["Corporation"],
                "card": row["Card"],
                "games": int(row["PlayerGames"]),
                "avg_elo": float(row["AvgEloChange"]),
            })
    return rows


def fuzzy_find_card(query, card_names):
    """Case-insensitive fuzzy match for a card name. Returns exact match or suggestions."""
    lower_map = {name.lower(): name for name in card_names}

    # Exact case-insensitive match
    if query.lower() in lower_map:
        return lower_map[query.lower()], []

    # Substring match
    substring_matches = [name for key, name in lower_map.items() if query.lower() in key]
    if len(substring_matches) == 1:
        return substring_matches[0], []
    if substring_matches:
        return None, substring_matches

    # Fuzzy match via difflib
    close = get_close_matches(query.lower(), lower_map.keys(), n=5, cutoff=0.4)
    suggestions = [lower_map[c] for c in close]
    return None, suggestions


def compute_synergies(card_name, combo_data, card_elo, corp_elo, min_games):
    """Compute synergy for every corporation paired with the given card."""
    card_baseline = card_elo[card_name][0]
    synergies = []

    for row in combo_data:
        if row["card"] != card_name:
            continue
        if row["games"] < min_games:
            continue
        corp = row["corporation"]
        if corp not in corp_elo:
            continue
        corp_baseline = corp_elo[corp][0]
        synergy = row["avg_elo"] - corp_baseline
        synergies.append({
            "corporation": corp,
            "synergy": synergy,
            "combo_elo": row["avg_elo"],
            "corp_baseline": corp_baseline,
            "games": row["games"],
        })

    synergies.sort(key=lambda x: x["synergy"], reverse=True)
    return synergies, card_baseline


def plot_synergies(card_name, card_baseline, synergies):
    """Horizontal bar chart of synergy gain per corporation."""
    corps = [f"{s['corporation']} ({s['corp_baseline']:+.2f})" for s in synergies]
    values = [s["synergy"] for s in synergies]
    combo_elos = [s["combo_elo"] for s in synergies]
    games = [s["games"] for s in synergies]
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in values]

    fig, ax = plt.subplots(figsize=(12, max(6, len(corps) * 0.45)))

    y_pos = np.arange(len(corps))
    bars = ax.barh(y_pos, values, color=colors, edgecolor="black", linewidth=0.5, alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(corps, fontsize=10)
    ax.invert_yaxis()

    # Annotate bars: positive labels after bar end, negative labels after zero line
    for i, (bar, val, combo, n) in enumerate(zip(bars, values, combo_elos, games)):
        label = f"{val:+.2f}  (combo: {combo:+.2f}, n={n})"
        if val >= 0:
            ax.text(val + 0.02, i, label, va="center", ha="left", fontsize=9)
        else:
            ax.text(0.02, i, label, va="center", ha="left", fontsize=9)

    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.set_xlabel("Lift over Corp Baseline (Elo)", fontsize=12)
    ax.set_title(
        f"Starting Hand Synergy: {card_name} ({card_baseline:+.2f})\n"
        f"lift = combo_elo - corp_elo",
        fontsize=13,
        fontweight="bold",
    )
    ax.grid(True, axis="x", alpha=0.3)

    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Show starting hand synergy between a card and each corporation."
    )
    parser.add_argument("card", help="Card name (case-insensitive, partial match supported)")
    parser.add_argument(
        "--min-games",
        type=int,
        default=30,
        help="Minimum games for a combo to be included (default: 30)",
    )
    args = parser.parse_args()

    # Paths
    data_dir = Path(__file__).parent / "starting_hand_stats"
    corp_csv = data_dir / "corporation_keep_stats.csv"
    card_csv = data_dir / "startinghand_card_keep_stats.csv"
    combo_csv = data_dir / "card_corporation_keep_stats.csv"

    for p in (corp_csv, card_csv, combo_csv):
        if not p.exists():
            print(f"Error: data file not found: {p}")
            sys.exit(1)

    # Load data
    corp_elo = load_csv_dict(corp_csv, "Corporation", "AvgEloChange")
    card_elo = load_csv_dict(card_csv, "Card", "AvgEloChange")
    combo_data = load_combo_data(combo_csv)

    # Resolve card name
    card_name, suggestions = fuzzy_find_card(args.card, list(card_elo.keys()))
    if card_name is None:
        print(f"Card not found: '{args.card}'")
        if suggestions:
            print("Did you mean:")
            for s in suggestions:
                print(f"  - {s}")
        sys.exit(1)

    if card_name != args.card:
        print(f"Matched: {card_name}")

    # Compute synergies
    synergies, card_baseline = compute_synergies(
        card_name, combo_data, card_elo, corp_elo, args.min_games
    )

    if not synergies:
        print(f"No corporation combos found for '{card_name}' with >= {args.min_games} games.")
        sys.exit(1)

    # Print table
    print(f"\nSynergy for: {card_name}  (baseline Elo: {card_baseline:+.2f})")
    print(f"Min games: {args.min_games}")
    print(f"{'Corporation':<35} {'Lift':>8} {'Combo Elo':>10} {'Corp Elo':>9} {'Games':>6}")
    print("-" * 72)
    for s in synergies:
        print(
            f"{s['corporation']:<35} {s['synergy']:>+8.2f} {s['combo_elo']:>+10.2f} "
            f"{s['corp_baseline']:>+9.2f} {s['games']:>6}"
        )

    # Plot
    plot_synergies(card_name, card_baseline, synergies)


if __name__ == "__main__":
    main()
