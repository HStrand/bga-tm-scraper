#!/usr/bin/env python3
"""
Generate draft priority summary statistics from detailed draft picks CSV.
Reads the detailed CSV and aggregates into summary statistics.
"""

import csv
from pathlib import Path
from collections import defaultdict


def generate_summary_from_detailed(detailed_csv_path, summary_csv_path):
    """Generate summary statistics from detailed draft picks."""

    print(f"Reading detailed draft picks from: {detailed_csv_path}")

    # Track statistics per card
    card_stats = defaultdict(lambda: {
        'pick1_count': 0,
        'pick2_count': 0,
        'pick3_count': 0,
        'pick4_count': 0,
        'total_picks': 0,
        'pick_positions': []
    })

    # Read detailed CSV
    with open(detailed_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')

        for row in reader:
            card = row['card']
            position = int(row['pick_position'])

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

    print(f"Processed {sum(s['total_picks'] for s in card_stats.values())} draft picks")
    print(f"Unique cards: {len(card_stats)}")

    # Calculate final statistics
    card_results = []
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

        card_results.append({
            'card_name': card,
            'total_picks': total,
            'avg_pick_position': round(avg_pick_position, 2),
            'pick1_count': stats['pick1_count'],
            'pick2_count': stats['pick2_count'],
            'pick3_count': stats['pick3_count'],
            'pick4_count': stats['pick4_count'],
            'pick1_pct': round(pick1_pct, 1),
            'pick2_pct': round(pick2_pct, 1),
            'pick3_pct': round(pick3_pct, 1),
            'pick4_pct': round(pick4_pct, 1),
            'priority_score': round(priority_score, 2)
        })

    # Sort by average pick position (lower is better)
    card_results.sort(key=lambda x: x['avg_pick_position'])

    # Write summary CSV
    fieldnames = ['card_name', 'total_picks', 'avg_pick_position',
                 'pick1_count', 'pick2_count', 'pick3_count', 'pick4_count',
                 'pick1_pct', 'pick2_pct', 'pick3_pct', 'pick4_pct',
                 'priority_score']

    with open(summary_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for result in card_results:
            writer.writerow(result)

    print(f"\nSummary saved to: {summary_csv_path}")
    print(f"Total cards: {len(card_results)}")

    # Display top 20
    print("\n" + "="*100)
    print("TOP 20 HIGHEST PRIORITY CARDS")
    print("="*100)
    print(f"\n{'Rank':<4} {'Card':<40} {'Total':<7} {'Avg Pos':<8} {'P1%':<7} {'P2%':<7} {'P3%':<7} {'P4%':<7}")
    print("-" * 100)

    for rank, result in enumerate(card_results[:20], 1):
        print(f"{rank:<4} {result['card_name']:<40} {result['total_picks']:<7} "
              f"{result['avg_pick_position']:<8.2f} "
              f"{result['pick1_pct']:<7.1f} {result['pick2_pct']:<7.1f} "
              f"{result['pick3_pct']:<7.1f} {result['pick4_pct']:<7.1f}")


def main():
    """Main function."""
    script_dir = Path(__file__).parent

    detailed_csv = script_dir / "draft_priority_detailed.csv"
    summary_csv = script_dir / "draft_priority_stats.csv"

    if not detailed_csv.exists():
        print(f"Error: Detailed CSV not found at {detailed_csv}")
        return

    generate_summary_from_detailed(detailed_csv, summary_csv)


if __name__ == "__main__":
    main()
