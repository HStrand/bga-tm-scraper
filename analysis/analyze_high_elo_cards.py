#!/usr/bin/env python3
"""
Analyze card statistics for high-ELO players from a detailed CSV file.

This script reads the 'card_stats_detailed.csv' file, filters for card plays
by players with an ELO rating of 600 or higher, and then calculates summary
statistics for each card based on this filtered data.

The summary includes win rate, average ELO change, and average ELO rating,
and is saved to 'card_stats_summary_600.csv'.
"""

import csv
from collections import defaultdict
from pathlib import Path

def analyze_high_elo_cards(input_file, output_file, elo_threshold=600):
    """
    Filters detailed card data for high-ELO players and generates a summary.
    """
    print(f"Starting High-ELO Card analysis (ELO >= {elo_threshold})...")
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file not found at {input_file}")
        return

    card_stats = defaultdict(lambda: {
        'total_played': 0,
        'total_wins': 0,
        'total_elo_change': 0,
        'total_elo_rating': 0,
        'elo_changes': [],
        'elo_ratings': [],
    })

    try:
        with open(input_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                try:
                    elo_rating = int(row.get('elo_rating', 0))
                    if elo_rating >= elo_threshold:
                        card = row['card']
                        won_game = row['won_game'] == 'True'
                        elo_change = int(row.get('elo_change', 0))

                        card_stats[card]['total_played'] += 1
                        if won_game:
                            card_stats[card]['total_wins'] += 1
                        
                        card_stats[card]['total_elo_change'] += elo_change
                        card_stats[card]['total_elo_rating'] += elo_rating
                        card_stats[card]['elo_changes'].append(elo_change)
                        card_stats[card]['elo_ratings'].append(elo_rating)

                except (ValueError, TypeError):
                    # Skip rows with invalid data
                    continue
    
    except Exception as e:
        print(f"Error reading or processing {input_file}: {e}")
        return

    print(f"Found {len(card_stats)} unique cards played by players with ELO >= {elo_threshold}")

    # Calculate final statistics
    card_results = {}
    for card, stats in card_stats.items():
        win_rate = stats['total_wins'] / stats['total_played'] if stats['total_played'] > 0 else 0
        avg_elo_change = stats['total_elo_change'] / len(stats['elo_changes']) if stats['elo_changes'] else 0
        avg_elo_rating = stats['total_elo_rating'] / len(stats['elo_ratings']) if stats['elo_ratings'] else 0
        
        card_results[card] = {
            'card': card,
            'total_played': stats['total_played'],
            'win_rate': win_rate,
            'avg_elo_change': avg_elo_change,
            'avg_elo_rating': avg_elo_rating,
        }

    # Save summary to CSV
    save_summary_to_csv(card_results, output_file)

def save_summary_to_csv(card_results, output_file):
    """Saves the summary statistics to a CSV file."""
    if not card_results:
        print("No results to save.")
        return

    try:
        fieldnames = ['card', 'total_played', 'win_rate', 'avg_elo_change', 'avg_elo_rating']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            sorted_cards = sorted(card_results.items(), key=lambda x: x[1]['avg_elo_change'], reverse=True)
            
            for card, stats in sorted_cards:
                row = {
                    'card': card,
                    'total_played': stats['total_played'],
                    'win_rate': round(stats['win_rate'], 4),
                    'avg_elo_change': round(stats['avg_elo_change'], 4),
                    'avg_elo_rating': round(stats['avg_elo_rating'], 1),
                }
                writer.writerow(row)
        
        print(f"High-ELO summary saved to: {output_file}")

    except Exception as e:
        print(f"Error saving summary CSV file: {e}")

def main():
    """Main function to run the high-ELO card analysis."""
    script_dir = Path(__file__).parent
    input_file = script_dir / "card_stats_detailed.csv"
    output_file = script_dir / "card_stats_summary_600.csv"
    
    print("Terraforming Mars - High-ELO Card Stats Analysis")
    print("=" * 50)
    
    analyze_high_elo_cards(input_file, output_file)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
