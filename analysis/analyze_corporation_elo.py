#!/usr/bin/env python3
"""
Analyze average ELO gained per corporation in Terraforming Mars games.

This script processes all parsed game files to calculate the average ELO rating change
(game_rank_change) for each corporation across all games. Unlike other analysis scripts
that focus on perspective players, this one examines all players in each game to get
a comprehensive view of corporation performance.

ELO data comes from the elo_data.game_rank_change field for each player.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
import csv
import matplotlib.pyplot as plt
import numpy as np

def normalize_corporation_name(raw_name):
    """
    Normalize corporation names to their full official names.
    Maps abbreviated or truncated names to their complete versions.
    """
    if not raw_name:
        return "Unknown"
    
    # Corporation name mapping dictionary
    name_mapping = {
        "Valley": "Valley Trust",
        "Mining": "Mining Guild",
        "Point": "Point Luna", 
        "Robinson": "Robinson Industries",
        "Cheung": "Cheung Shing Mars",
        "Interplanetary": "Interplanetary Cinematics",
        "Tharsis": "Tharsis Republic",
        "Saturn": "Saturn Systems",
        # Keep full names as-is
        "Valley Trust": "Valley Trust",
        "Mining Guild": "Mining Guild",
        "Point Luna": "Point Luna",
        "Robinson Industries": "Robinson Industries", 
        "Cheung Shing Mars": "Cheung Shing Mars",
        "Interplanetary Cinematics": "Interplanetary Cinematics",
        "Tharsis Republic": "Tharsis Republic",
        "Saturn Systems": "Saturn Systems",
        "CrediCor": "CrediCor",
        "Ecoline": "Ecoline",
        "Helion": "Helion",
        "Inventrix": "Inventrix",
        "PhoboLog": "PhoboLog",
        "Teractor": "Teractor",
        "ThorGate": "ThorGate",
        "United Nations Mars Initiative": "United Nations Mars Initiative",
        "Vitor": "Vitor"
    }
    
    # Return mapped name or original if not found in mapping
    return name_mapping.get(raw_name, raw_name)

def process_game_for_elo_data(file_path):
    """
    Process a single game file to extract ELO data for all players.
    Returns list of (corporation, elo_change) tuples or empty list if processing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        # Get all players from the game
        players = game_data.get('players', {})
        if not players:
            print(f"Warning: No players found in {file_path}")
            return []
        
        elo_data_list = []
        
        # Extract corporation and ELO change for each player
        for player_id, player_data in players.items():
            corporation = player_data.get('corporation')
            elo_data = player_data.get('elo_data')
            
            if not corporation:
                print(f"Warning: No corporation found for player {player_id} in {file_path}")
                continue
            
            # Check if elo_data exists and is not None
            if not elo_data or not isinstance(elo_data, dict):
                print(f"Warning: No elo_data found for player {player_id} ({corporation}) in {file_path}")
                continue
            
            # Get ELO change (game_rank_change) and rating (game_rank)
            elo_change = elo_data.get('game_rank_change')
            elo_rating = elo_data.get('game_rank')
            
            if elo_change is None:
                print(f"Warning: No game_rank_change found for player {player_id} ({corporation}) in {file_path}")
                continue
            
            # Normalize corporation name
            normalized_corporation = normalize_corporation_name(corporation)
            
            # Add to results
            elo_data_list.append({
                'corporation': normalized_corporation,
                'elo_change': elo_change,
                'elo_rating': elo_rating,
                'player_id': player_id,
                'player_name': player_data.get('player_name', 'Unknown'),
                'replay_id': game_data.get('replay_id', 'unknown'),
                'game_date': game_data.get('game_date', 'unknown')
            })
        
        return elo_data_list
        
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
    
    # Look for all JSON files in player subdirectories
    for player_dir in data_path.iterdir():
        if player_dir.is_dir() and player_dir.name.isdigit():
            for game_file in player_dir.glob("*.json"):
                game_files.append(game_file)
    
    return game_files

def analyze_corporation_elo(data_dir):
    """
    Main analysis function that processes all games and calculates corporation ELO statistics.
    """
    print("Starting Corporation ELO analysis...")
    
    # Find all game files
    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")
    
    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, []
    
    # Data structures for aggregation
    corporation_stats = defaultdict(lambda: {
        'total_elo_change': 0,
        'total_elo_rating': 0,
        'game_count': 0,
        'elo_changes': [],  # For calculating statistics
        'elo_ratings': [],  # For calculating average ELO rating
        'player_instances': []  # For detailed tracking
    })
    
    all_elo_data = []
    total_games_processed = 0
    total_player_instances = 0
    
    # Process each game file
    for i, game_file in enumerate(game_files):
        elo_data_list = process_game_for_elo_data(game_file)
        
        if elo_data_list:
            total_games_processed += 1
            
            # Process each player's data from this game
            for elo_data in elo_data_list:
                corporation = elo_data['corporation']
                elo_change = elo_data['elo_change']
                elo_rating = elo_data['elo_rating']
                
                # Update corporation statistics
                corporation_stats[corporation]['total_elo_change'] += elo_change
                corporation_stats[corporation]['game_count'] += 1
                corporation_stats[corporation]['elo_changes'].append(elo_change)
                
                # Update ELO rating statistics if available
                if elo_rating is not None:
                    corporation_stats[corporation]['total_elo_rating'] += elo_rating
                    corporation_stats[corporation]['elo_ratings'].append(elo_rating)
                
                corporation_stats[corporation]['player_instances'].append(elo_data)
                
                # Add to overall data
                all_elo_data.append(elo_data)
                total_player_instances += 1
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} games...")
    
    print(f"\nAnalysis complete!")
    print(f"Games processed: {total_games_processed}")
    print(f"Total player instances: {total_player_instances}")
    print(f"Unique corporations: {len(corporation_stats)}")
    
    # Calculate final statistics for each corporation
    corporation_results = {}
    for corporation, stats in corporation_stats.items():
        avg_elo_change = stats['total_elo_change'] / stats['game_count']
        
        # Calculate additional statistics
        elo_changes = stats['elo_changes']
        elo_ratings = stats['elo_ratings']
        avg_elo_rating = stats['total_elo_rating'] / len(elo_ratings) if elo_ratings else 0
        min_elo = min(elo_changes)
        max_elo = max(elo_changes)
        
        # Calculate win rate (positive ELO changes)
        positive_changes = [x for x in elo_changes if x > 0]
        win_rate = len(positive_changes) / len(elo_changes) if elo_changes else 0
        
        corporation_results[corporation] = {
            'corporation': corporation,
            'game_count': stats['game_count'],
            'total_elo_change': stats['total_elo_change'],
            'avg_elo_change': avg_elo_change,
            'avg_elo_rating': avg_elo_rating,
            'min_elo_change': min_elo,
            'max_elo_change': max_elo,
            'win_rate': win_rate,
            'elo_rating_instances': len(elo_ratings),
            'player_instances': stats['player_instances']
        }
    
    return corporation_results, all_elo_data

def display_results(corporation_results):
    """Display analysis results."""
    if not corporation_results:
        print("No results to display.")
        return
    
    print("\n" + "="*100)
    print("CORPORATION ELO ANALYSIS RESULTS")
    print("="*100)
    print("Average ELO change (game_rank_change) per corporation")
    print("Positive values indicate corporations that tend to gain ELO rating")
    print("="*100)
    
    # Sort corporations by average ELO change (descending)
    sorted_corps = sorted(corporation_results.items(), 
                         key=lambda x: x[1]['avg_elo_change'], 
                         reverse=True)
    
    print(f"\n{'Rank':<4} {'Corporation':<25} {'Games':<6} {'Avg ELO Δ':<9} {'Avg ELO':<8} {'Total':<7} {'Min':<6} {'Max':<6} {'Win%':<6}")
    print("-" * 110)
    
    for rank, (corporation, stats) in enumerate(sorted_corps, 1):
        print(f"{rank:<4} {corporation:<25} {stats['game_count']:<6} "
              f"{stats['avg_elo_change']:<9.2f} {stats['avg_elo_rating']:<8.0f} {stats['total_elo_change']:<7} "
              f"{stats['min_elo_change']:<6} {stats['max_elo_change']:<6} "
              f"{stats['win_rate']*100:<6.1f}")
    
    # Calculate overall statistics
    all_avg_elos = [stats['avg_elo_change'] for stats in corporation_results.values()]
    all_game_counts = [stats['game_count'] for stats in corporation_results.values()]
    
    overall_avg = sum(all_avg_elos) / len(all_avg_elos)
    total_games = sum(all_game_counts)
    
    print(f"\n{'='*100}")
    print(f"SUMMARY STATISTICS:")
    print(f"Total corporation instances: {total_games}")
    print(f"Overall average ELO change: {overall_avg:.3f}")
    print(f"Best performing: {sorted_corps[0][0]} (+{sorted_corps[0][1]['avg_elo_change']:.2f})")
    print(f"Worst performing: {sorted_corps[-1][0]} ({sorted_corps[-1][1]['avg_elo_change']:.2f})")
    print(f"{'='*100}")

def save_detailed_results_to_csv(all_elo_data, output_file):
    """Save detailed game-by-game results to a CSV file."""
    if not all_elo_data:
        print("No detailed results to save.")
        return
    
    try:
        fieldnames = ['corporation', 'elo_change', 'elo_rating', 'player_id', 'player_name', 
                     'replay_id', 'game_date']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by corporation, then by game_date
            sorted_results = sorted(all_elo_data, 
                                  key=lambda x: (x['corporation'], x['game_date']))
            
            for result in sorted_results:
                writer.writerow(result)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving detailed CSV file: {e}")

def save_corporation_summary_to_csv(corporation_results, output_file):
    """Save corporation summary statistics to a CSV file."""
    if not corporation_results:
        print("No corporation summary to save.")
        return
    
    try:
        fieldnames = ['corporation', 'game_count', 'total_elo_change', 'avg_elo_change', 
                     'avg_elo_rating', 'min_elo_change', 'max_elo_change', 'win_rate', 'elo_rating_instances']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by average ELO change (descending)
            sorted_corps = sorted(corporation_results.items(), 
                                key=lambda x: x[1]['avg_elo_change'], 
                                reverse=True)
            
            for corporation, stats in sorted_corps:
                row = {
                    'corporation': corporation,
                    'game_count': stats['game_count'],
                    'total_elo_change': stats['total_elo_change'],
                    'avg_elo_change': round(stats['avg_elo_change'], 4),
                    'avg_elo_rating': round(stats['avg_elo_rating'], 1),
                    'min_elo_change': stats['min_elo_change'],
                    'max_elo_change': stats['max_elo_change'],
                    'win_rate': round(stats['win_rate'], 4),
                    'elo_rating_instances': stats['elo_rating_instances']
                }
                writer.writerow(row)
        
        print(f"Corporation summary saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving corporation summary CSV file: {e}")

def plot_corporation_elo_histograms(corporation_results, output_dir, min_games=10):
    """
    Plot histograms showing ELO gain distribution for each corporation.
    
    Args:
        corporation_results: Dictionary containing corporation statistics
        output_dir: Directory to save histogram plots
        min_games: Minimum number of games required to generate a histogram
    """
    if not corporation_results:
        print("No corporation results to plot.")
        return
    
    # Filter corporations with sufficient data
    corporations_to_plot = {
        corp: stats for corp, stats in corporation_results.items() 
        if stats['game_count'] >= min_games
    }
    
    if not corporations_to_plot:
        print(f"No corporations have at least {min_games} games. Skipping histogram generation.")
        return
    
    print(f"\nGenerating ELO distribution histograms for {len(corporations_to_plot)} corporations...")
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Determine overall ELO range for consistent binning
    all_elo_changes = []
    for stats in corporations_to_plot.values():
        all_elo_changes.extend(stats['player_instances'])
    
    if not all_elo_changes:
        print("No ELO change data found.")
        return
    
    # Extract just the ELO change values
    elo_values = [data['elo_change'] for data in all_elo_changes]
    min_elo = min(elo_values)
    max_elo = max(elo_values)
    
    # Create bins with 2 ELO point intervals
    bin_width = 2
    bin_start = int(min_elo // bin_width) * bin_width - bin_width
    bin_end = int(max_elo // bin_width) * bin_width + bin_width * 2
    bins = np.arange(bin_start, bin_end + bin_width, bin_width)
    
    print(f"Using ELO range: {bin_start} to {bin_end} with {bin_width}-point bins")
    
    # Sort corporations by average ELO change for consistent ordering
    sorted_corporations = sorted(corporations_to_plot.items(), 
                               key=lambda x: x[1]['avg_elo_change'], 
                               reverse=True)
    
    # Generate histogram for each corporation
    for corporation, stats in sorted_corporations:
        elo_changes = [data['elo_change'] for data in stats['player_instances']]
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        # Create histogram
        n, bins_used, patches = plt.hist(elo_changes, bins=bins, alpha=0.7, 
                                       color='steelblue', edgecolor='black', linewidth=0.5)
        
        # Color bars based on positive/negative ELO changes
        for i, (patch, bin_left) in enumerate(zip(patches, bins_used[:-1])):
            bin_center = bin_left + bin_width / 2
            if bin_center > 0:
                patch.set_facecolor('green')
                patch.set_alpha(0.6)
            elif bin_center < 0:
                patch.set_facecolor('red')
                patch.set_alpha(0.6)
            else:
                patch.set_facecolor('gray')
                patch.set_alpha(0.6)
        
        # Add vertical line at zero
        plt.axvline(x=0, color='black', linestyle='--', linewidth=2, alpha=0.8)
        
        # Add vertical line for average ELO change
        avg_elo = stats['avg_elo_change']
        plt.axvline(x=avg_elo, color='orange', linestyle='-', linewidth=3, 
                   label=f'Average: {avg_elo:.2f}')
        
        # Formatting
        plt.title(f'ELO Gain Distribution - {corporation}\n'
                 f'({stats["game_count"]} games, Win Rate: {stats["win_rate"]*100:.1f}%, Avg ELO: {stats["avg_elo_rating"]:.0f})', 
                 fontsize=16, fontweight='bold')
        plt.xlabel('ELO Change', fontsize=14)
        plt.ylabel('Frequency', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=12)
        
        # Add statistics text box
        stats_text = f'Min: {stats["min_elo_change"]}\n' \
                    f'Max: {stats["max_elo_change"]}\n' \
                    f'Avg: {avg_elo:.2f}\n' \
                    f'Games: {stats["game_count"]}'
        
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                fontsize=11, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Set x-axis limits with some padding
        plt.xlim(bin_start, bin_end)
        
        # Improve layout
        plt.tight_layout()
        
        # Save the plot
        safe_corp_name = corporation.replace(' ', '_').replace('/', '_')
        filename = f'corporation_elo_histogram_{safe_corp_name}.png'
        filepath = output_path / filename
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved histogram for {corporation}: {filename}")
    
    print(f"\nHistogram generation complete! {len(sorted_corporations)} plots saved to {output_path}")

def main():
    """Main function to run the Corporation ELO analysis."""
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    output_dir = script_dir / "data"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    detailed_output_file = output_dir / "corporation_elo_detailed.csv"
    summary_output_file = output_dir / "corporation_elo_summary.csv"
    
    print("Terraforming Mars - Corporation ELO Analysis")
    print("=" * 50)
    
    # Run the analysis
    corporation_results, all_elo_data = analyze_corporation_elo(data_dir)
    
    if corporation_results:
        # Display results
        display_results(corporation_results)
        
        # Save to CSV files
        save_detailed_results_to_csv(all_elo_data, detailed_output_file)
        save_corporation_summary_to_csv(corporation_results, summary_output_file)
        
        # Generate ELO distribution histograms
        plot_corporation_elo_histograms(corporation_results, output_dir, min_games=10)
        
        print(f"\nAnalysis complete! Check the CSV files and histogram plots in {output_dir} for detailed data.")
    else:
        print("No data found to analyze.")

if __name__ == "__main__":
    main()
