#!/usr/bin/env python3
"""
Analyze draft priorities in Terraforming Mars games.

This script processes all parsed game files to identify which cards have the highest
draft priority by tracking at which pick position (1st, 2nd, 3rd, 4th) cards are
drafted when they appear in draft options.

In draft mode, card_options shows the cards REMAINING after a pick (passed to opponent).
The number of remaining cards indicates the pick position:
- 3 cards remaining = 1st pick (started with 4, picked 1, passing 3)
- 2 cards remaining = 2nd pick (started with 3, picked 1, passing 2)
- 1 card remaining = 3rd pick (started with 2, picked 1, passing 1)
  - The remaining card is also registered as the 4th pick for that player
- 0 cards remaining = 4th pick (last card, nothing to pass)

Cards picked earlier (higher priority) have more cards remaining to pass.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
import csv


def process_game_for_draft_data(file_path):
    """
    Process a single game file to extract draft pick data.
    Returns list of draft pick dictionaries or empty list if processing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)

        # Skip games without draft mode
        if not game_data.get('draft_on'):
            return []

        moves = game_data.get('moves', [])
        if not moves:
            return []

        draft_picks = []

        for move in moves:
            if move.get('action_type') != 'draft':
                continue

            player_id = move.get('player_id')
            card_drafted = move.get('card_drafted')
            card_options = move.get('card_options')

            # Skip if no card was drafted
            if not card_drafted:
                continue

            # Get the cards remaining after this pick (being passed to opponent)
            remaining_cards = card_options.get(player_id, []) if card_options else []
            num_remaining = len(remaining_cards)

            # Determine pick position based on cards remaining after the pick
            # 3 cards remaining = 1st pick (started with 4, picked 1, passing 3)
            # 2 cards remaining = 2nd pick (started with 3, picked 1, passing 2)
            # 1 card remaining = 3rd pick (started with 2, picked 1, passing 1)
            # 0 cards remaining = 4th pick (started with 1, picked 1, nothing to pass)
            if num_remaining == 3:
                pick_position = 1
            elif num_remaining == 2:
                pick_position = 2
            elif num_remaining == 1:
                pick_position = 3
            elif num_remaining == 0:
                pick_position = 4
            else:
                # Skip invalid cases
                continue

            # Record the drafted card
            draft_pick = {
                'card': card_drafted,
                'pick_position': pick_position,
                'replay_id': game_data.get('replay_id', 'unknown'),
                'game_date': game_data.get('game_date', 'unknown'),
                'player_id': player_id
            }
            draft_picks.append(draft_pick)

            # If this was a 3rd pick (1 card remaining), also register the remaining card as 4th pick
            if num_remaining == 1 and remaining_cards:
                last_card = remaining_cards[0]
                fourth_pick = {
                    'card': last_card,
                    'pick_position': 4,
                    'replay_id': game_data.get('replay_id', 'unknown'),
                    'game_date': game_data.get('game_date', 'unknown'),
                    'player_id': player_id
                }
                draft_picks.append(fourth_pick)

        return draft_picks

    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print(f"Warning: Could not process {file_path}: {e}")
        return []


def find_all_game_files(data_dir):
    """Find all JSON game files in the parsed data directory."""
    game_files = []
    data_path = Path(data_dir)

    if not data_path.exists():
        print(f"Error: Data directory {data_dir} does not exist")
        return game_files

    for player_dir in data_path.iterdir():
        if player_dir.is_dir() and player_dir.name.isdigit():
            for game_file in player_dir.glob("*.json"):
                game_files.append(game_file)

    return game_files


def analyze_draft_priority(data_dir):
    """
    Main analysis function that processes all games and calculates draft statistics.
    """
    print("Starting Draft Priority analysis...")

    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")

    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, []

    # Track statistics per card
    card_stats = defaultdict(lambda: {
        'pick1_count': 0,
        'pick2_count': 0,
        'pick3_count': 0,
        'pick4_count': 0,
        'total_picks': 0,
        'pick_positions': []
    })

    all_draft_picks = []
    total_games_processed = 0
    total_draft_picks = 0

    for i, game_file in enumerate(game_files):
        draft_picks = process_game_for_draft_data(game_file)

        if draft_picks:
            total_games_processed += 1

            for pick in draft_picks:
                card = pick['card']
                position = pick['pick_position']

                card_stats[card]['total_picks'] += 1
                card_stats[card]['pick_positions'].append(position)

                # Increment position-specific counter
                if position == 1:
                    card_stats[card]['pick1_count'] += 1
                elif position == 2:
                    card_stats[card]['pick2_count'] += 1
                elif position == 3:
                    card_stats[card]['pick3_count'] += 1
                elif position == 4:
                    card_stats[card]['pick4_count'] += 1

                all_draft_picks.append(pick)
                total_draft_picks += 1

        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} games...")

    print(f"\nAnalysis complete!")
    print(f"Games with draft data processed: {total_games_processed}")
    print(f"Total draft picks: {total_draft_picks}")
    print(f"Unique cards drafted: {len(card_stats)}")

    # Calculate final statistics
    card_results = {}
    for card, stats in card_stats.items():
        total = stats['total_picks']

        # Calculate average pick position
        avg_pick_position = sum(stats['pick_positions']) / len(stats['pick_positions']) if stats['pick_positions'] else 0

        # Calculate percentages
        pick1_pct = (stats['pick1_count'] / total * 100) if total > 0 else 0
        pick2_pct = (stats['pick2_count'] / total * 100) if total > 0 else 0
        pick3_pct = (stats['pick3_count'] / total * 100) if total > 0 else 0
        pick4_pct = (stats['pick4_count'] / total * 100) if total > 0 else 0

        # Calculate priority score (weighted: 4 points for pick1, 3 for pick2, etc.)
        priority_score = (
            stats['pick1_count'] * 4 +
            stats['pick2_count'] * 3 +
            stats['pick3_count'] * 2 +
            stats['pick4_count'] * 1
        ) / total if total > 0 else 0

        card_results[card] = {
            'card_name': card,
            'total_picks': total,
            'avg_pick_position': avg_pick_position,
            'pick1_count': stats['pick1_count'],
            'pick2_count': stats['pick2_count'],
            'pick3_count': stats['pick3_count'],
            'pick4_count': stats['pick4_count'],
            'pick1_pct': pick1_pct,
            'pick2_pct': pick2_pct,
            'pick3_pct': pick3_pct,
            'pick4_pct': pick4_pct,
            'priority_score': priority_score
        }

    return card_results, all_draft_picks


def display_results(card_results):
    """Display analysis results."""
    if not card_results:
        print("No results to display.")
        return

    print("\n" + "="*120)
    print("DRAFT PRIORITY ANALYSIS RESULTS")
    print("="*120)

    # Sort by average pick position (lower is better)
    sorted_cards = sorted(card_results.items(),
                         key=lambda x: x[1]['avg_pick_position'])

    print(f"\n{'Rank':<4} {'Card':<40} {'Total':<7} {'Avg Pos':<8} "
          f"{'P1%':<7} {'P2%':<7} {'P3%':<7} {'P4%':<7} {'Priority':<8}")
    print("-" * 120)

    for rank, (card, stats) in enumerate(sorted_cards[:50], 1):  # Show top 50
        print(f"{rank:<4} {card:<40} {stats['total_picks']:<7} "
              f"{stats['avg_pick_position']:<8.2f} "
              f"{stats['pick1_pct']:<7.1f} {stats['pick2_pct']:<7.1f} "
              f"{stats['pick3_pct']:<7.1f} {stats['pick4_pct']:<7.1f} "
              f"{stats['priority_score']:<8.2f}")

    print(f"\nShowing top 50 cards by draft priority (lower avg position = higher priority)")


def save_summary_to_csv(card_results, output_file):
    """Save card draft priority summary to a CSV file."""
    if not card_results:
        print("No summary to save.")
        return

    try:
        fieldnames = ['card_name', 'total_picks', 'avg_pick_position',
                     'pick1_count', 'pick2_count', 'pick3_count', 'pick4_count',
                     'pick1_pct', 'pick2_pct', 'pick3_pct', 'pick4_pct',
                     'priority_score']

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writeheader()

            # Sort by average pick position (lower is better)
            sorted_cards = sorted(card_results.items(),
                                 key=lambda x: x[1]['avg_pick_position'])

            for card, stats in sorted_cards:
                row = {
                    'card_name': stats['card_name'],
                    'total_picks': stats['total_picks'],
                    'avg_pick_position': round(stats['avg_pick_position'], 2),
                    'pick1_count': stats['pick1_count'],
                    'pick2_count': stats['pick2_count'],
                    'pick3_count': stats['pick3_count'],
                    'pick4_count': stats['pick4_count'],
                    'pick1_pct': round(stats['pick1_pct'], 1),
                    'pick2_pct': round(stats['pick2_pct'], 1),
                    'pick3_pct': round(stats['pick3_pct'], 1),
                    'pick4_pct': round(stats['pick4_pct'], 1),
                    'priority_score': round(stats['priority_score'], 2)
                }
                writer.writerow(row)

        print(f"\nDraft priority summary saved to: {output_file}")

    except Exception as e:
        print(f"Error saving summary CSV file: {e}")


def save_detailed_to_csv(all_draft_picks, output_file):
    """Save detailed pick-by-pick data to a CSV file."""
    if not all_draft_picks:
        print("No detailed picks to save.")
        return

    try:
        fieldnames = ['card', 'pick_position', 'replay_id', 'game_date', 'player_id']

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writeheader()

            sorted_picks = sorted(all_draft_picks,
                                key=lambda x: (x['card'], x['game_date']))

            for pick in sorted_picks:
                writer.writerow(pick)

        print(f"Detailed draft picks saved to: {output_file}")

    except Exception as e:
        print(f"Error saving detailed CSV file: {e}")


def main():
    """Main function to run the Draft Priority analysis."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    output_dir = script_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    summary_output_file = output_dir / "draft_priority_stats.csv"
    detailed_output_file = output_dir / "draft_priority_detailed.csv"

    print("Terraforming Mars - Draft Priority Analysis")
    print("=" * 50)

    card_results, all_draft_picks = analyze_draft_priority(data_dir)

    if card_results:
        display_results(card_results)

        save_summary_to_csv(card_results, summary_output_file)
        save_detailed_to_csv(all_draft_picks, detailed_output_file)

        print(f"\nAnalysis complete! Check the CSV files in {output_dir} for detailed data.")
    else:
        print("No draft data found to analyze.")


if __name__ == "__main__":
    main()
