#!/usr/bin/env python3
"""
Summarize animal card VP data from a detailed CSV file, with optional Elo filters.
"""

import argparse
import csv
import pandas as pd
from collections import defaultdict
import statistics
from pathlib import Path

def summarize_animal_cards(input_file, output_file, min_player_elo=None, min_opponent_elo=None):
    """
    Reads a detailed CSV of animal card data, applies optional Elo filters,
    and generates a summary CSV.
    """
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        return

    # Filter by player Elo
    if min_player_elo is not None:
        df = df[df['player_elo'] >= min_player_elo]

    # Filter by opponent Elo
    if min_opponent_elo is not None:
        df = df[df['opponent_elo'] >= min_opponent_elo]

    if df.empty:
        print("No data left after filtering. No summary will be generated.")
        return

    # Data structures for aggregation
    card_stats = defaultdict(lambda: {
        'total_vp': 0,
        'total_stolen_vp': 0,
        'total_plants_denied_opponent': 0,
        'total_plants_denied_self': 0,
        'times_played': 0,
        'vp_values': [],
        'stolen_vp_values': [],
        'plants_denied_opponent_values': [],
        'plants_denied_self_values': [],
    })

    # Process each row in the filtered DataFrame
    for _, row in df.iterrows():
        card_name = row['card_name']
        vp_value = row['vp']
        stolen_vp = row.get('stolen_vp', 0)
        plants_denied_opponent = row.get('plants_denied_opponent', 0)
        plants_denied_self = row.get('plants_denied_self', 0)

        # Update card statistics
        card_stats[card_name]['total_vp'] += vp_value
        card_stats[card_name]['times_played'] += 1
        card_stats[card_name]['vp_values'].append(vp_value)

        if stolen_vp > 0:
            card_stats[card_name]['total_stolen_vp'] += stolen_vp
            card_stats[card_name]['stolen_vp_values'].append(stolen_vp)
        
        if plants_denied_opponent > 0:
            card_stats[card_name]['total_plants_denied_opponent'] += plants_denied_opponent
            card_stats[card_name]['plants_denied_opponent_values'].append(plants_denied_opponent)

        if plants_denied_self > 0:
            card_stats[card_name]['total_plants_denied_self'] += plants_denied_self
            card_stats[card_name]['plants_denied_self_values'].append(plants_denied_self)

    # Calculate final statistics for each card type
    card_results = {}
    for card_name, stats in card_stats.items():
        if stats['times_played'] > 0:
            avg_vp = stats['total_vp'] / stats['times_played']
            avg_stolen_vp = stats['total_stolen_vp'] / stats['times_played'] if stats['times_played'] > 0 else 0
            avg_plants_denied_opponent = stats['total_plants_denied_opponent'] / stats['times_played'] if stats['times_played'] > 0 else 0
            avg_plants_denied_self = stats['total_plants_denied_self'] / stats['times_played'] if stats['times_played'] > 0 else 0
            
            vp_values = stats['vp_values']
            min_vp = min(vp_values)
            max_vp = max(vp_values)
            std_dev = statistics.stdev(vp_values) if len(vp_values) > 1 else 0
            
            card_results[card_name] = {
                'card_name': card_name,
                'times_played': stats['times_played'],
                'total_vp': stats['total_vp'],
                'avg_vp': avg_vp,
                'avg_stolen_vp': avg_stolen_vp,
                'avg_plants_denied_opponent': avg_plants_denied_opponent,
                'avg_plants_denied_self': avg_plants_denied_self,
                'min_vp': min_vp,
                'max_vp': max_vp,
                'std_dev': std_dev,
            }

    # Save summary to CSV
    save_summary_to_csv(card_results, output_file)

def save_summary_to_csv(card_results, output_file):
    """Save card summary statistics to a CSV file."""
    if not card_results:
        print("No card summary to save.")
        return
    
    try:
        fieldnames = ['card_name', 'times_played', 'total_vp', 'avg_vp', 
                     'avg_stolen_vp', 'avg_plants_denied_opponent', 'avg_plants_denied_self', 
                     'min_vp', 'max_vp', 'std_dev']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            sorted_cards = sorted(card_results.items(), key=lambda x: x[1]['avg_vp'], reverse=True)
            
            for card_name, stats in sorted_cards:
                row = {
                    'card_name': card_name,
                    'times_played': stats['times_played'],
                    'total_vp': stats['total_vp'],
                    'avg_vp': round(stats['avg_vp'], 4),
                    'avg_stolen_vp': round(stats.get('avg_stolen_vp', 0), 4),
                    'avg_plants_denied_opponent': round(stats.get('avg_plants_denied_opponent', 0), 4),
                    'avg_plants_denied_self': round(stats.get('avg_plants_denied_self', 0), 4),
                    'min_vp': stats['min_vp'],
                    'max_vp': stats['max_vp'],
                    'std_dev': round(stats['std_dev'], 4)
                }
                writer.writerow(row)
        
        print(f"Summary results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving card summary CSV file: {e}")

def main():
    """Main function to parse arguments and run the summarization."""
    script_dir = Path(__file__).parent
    default_input = script_dir / "data" / "animal_cards_vp_detailed.csv"
    default_output = script_dir / "data" / "animal_cards_vp_summary_filtered.csv"

    parser = argparse.ArgumentParser(description="Summarize animal card VP data with optional Elo filters.")
    parser.add_argument('--input-file', type=str, default=str(default_input),
                        help='Path to the detailed input CSV file.')
    parser.add_argument('--output-file', type=str, default=str(default_output),
                        help='Path to the output summary CSV file.')
    parser.add_argument('--min-player-elo', type=int,
                        help='Minimum Elo of the player.')
    parser.add_argument('--min-opponent-elo', type=int,
                        help='Minimum Elo of the opponent.')

    args = parser.parse_args()

    print("Starting animal cards VP summarization...")
    summarize_animal_cards(args.input_file, args.output_file, args.min_player_elo, args.min_opponent_elo)
    print("Summarization complete.")

if __name__ == "__main__":
    main()
