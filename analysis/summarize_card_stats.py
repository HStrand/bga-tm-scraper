#!/usr/bin/env python3
"""
Summarize card stats data from a detailed CSV file, with an optional Elo filter.
"""

import argparse
import pandas as pd
from pathlib import Path

def summarize_card_stats(input_file, output_file, min_elo=None, min_opponent_elo=None):
    """
    Reads a detailed CSV of card stats data, applies an optional Elo filter,
    and generates a summary CSV.
    """
    try:
        df = pd.read_csv(input_file, delimiter=';')
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        return

    # Filter by player Elo
    if min_elo is not None:
        df = df[df['elo_rating'] >= min_elo]

    # Filter by opponent Elo
    if min_opponent_elo is not None:
        df = df[df['opponent_elo'] >= min_opponent_elo]

    if df.empty:
        print("No data left after filtering. No summary will be generated.")
        return

    # Group by card name and calculate summary statistics
    summary = df.groupby('card').agg(
        times_played=('card', 'size'),
        wins=('won_game', lambda x: x.sum()),
        total_vp=('final_vp', 'sum'),
        total_elo_change=('elo_change', 'sum')
    ).reset_index()

    summary['win_rate'] = (summary['wins'] / summary['times_played']) * 100
    summary['avg_vp'] = summary['total_vp'] / summary['times_played']
    summary['avg_elo_gain'] = summary['total_elo_change'] / summary['times_played']

    # Sort by win_rate
    summary = summary.sort_values(by='win_rate', ascending=False)

    # Save summary to CSV
    try:
        summary.to_csv(output_file, index=False, columns=['card', 'times_played', 'wins', 'win_rate', 'avg_vp', 'avg_elo_gain'])
        print(f"Summary results saved to: {output_file}")
    except Exception as e:
        print(f"Error saving card summary CSV file: {e}")

def main():
    """Main function to parse arguments and run the summarization."""
    script_dir = Path(__file__).parent
    default_input = script_dir / "data" / "card_stats_detailed.csv"
    default_output = script_dir / "data" / "card_stats_summary_filtered.csv"

    parser = argparse.ArgumentParser(description="Summarize card stats data with an optional Elo filter.")
    parser.add_argument('--input-file', type=str, default=str(default_input),
                        help='Path to the detailed input CSV file.')
    parser.add_argument('--output-file', type=str, default=str(default_output),
                        help='Path to the output summary CSV file.')
    parser.add_argument('--min-elo', type=int,
                        help='Minimum Elo of the player.')
    parser.add_argument('--min-opponent-elo', type=int,
                        help='Minimum Elo of the opponent.')

    args = parser.parse_args()

    print("Starting card stats summarization...")
    summarize_card_stats(args.input_file, args.output_file, args.min_elo, args.min_opponent_elo)
    print("Summarization complete.")

if __name__ == "__main__":
    main()
