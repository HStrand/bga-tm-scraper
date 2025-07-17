#!/usr/bin/env python3
"""
Analyze win rates per prelude card in Terraforming Mars games.

This script processes all parsed game files to calculate the win rate for each prelude card.
Win rate is defined as the percentage of games won (1st place) when a specific
prelude card was played by the player.

Prelude cards are identified by checking which cards in the cards_played array
match the prelude names defined in preludes.json. The winner is determined using
the 'winner' field from the game data.

When a player plays multiple preludes in a single game, each prelude is counted
as a separate data point for analysis.
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

def load_prelude_list():
    """
    Load the list of prelude cards from preludes.json.
    Returns a set of prelude card names for fast lookup.
    """
    try:
        script_dir = Path(__file__).parent
        preludes_file = script_dir / "preludes.json"
        
        with open(preludes_file, 'r', encoding='utf-8') as f:
            preludes_data = json.load(f)
        
        return set(preludes_data.get('preludes', []))
        
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print(f"Error loading preludes.json: {e}")
        return set()

def extract_preludes_from_player(player_data, prelude_set):
    """
    Extract prelude cards from a player's cards_played array by checking
    which cards are in the prelude set.
    
    Args:
        player_data: Dictionary containing player information
        prelude_set: Set of prelude card names for fast lookup
        
    Returns:
        List of prelude card names
    """
    cards_played = player_data.get('cards_played', [])
    
    if not cards_played or not prelude_set:
        return []
    
    # Filter cards_played to only include preludes
    preludes = [card for card in cards_played if card in prelude_set]
    
    return preludes

def determine_game_winner(game_data, players):
    """
    Determine the winner using the 'winner' field from game data.
    Returns the player_id of the winner by matching player_name.
    """
    winner_name = game_data.get('winner')
    if not winner_name:
        return None
    
    # Find player_id by matching player_name
    for player_id, player_data in players.items():
        if player_data.get('player_name') == winner_name:
            return player_id
    
    return None

def process_game_for_prelude_data(file_path, prelude_set):
    """
    Process a single game file to extract prelude data and determine winner.
    Returns list of prelude data dictionaries or empty list if processing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        # Get all players from the game
        players = game_data.get('players', {})
        if not players:
            print(f"Warning: No players found in {file_path}")
            return []
        
        # Determine the winner using the winner field
        winner_id = determine_game_winner(game_data, players)
        if not winner_id:
            print(f"Warning: Could not determine winner in {file_path}")
            return []
        
        prelude_data_list = []
        
        # Extract prelude data for each player
        for player_id, player_data in players.items():
            preludes = extract_preludes_from_player(player_data, prelude_set)
            
            # Skip players who don't have preludes
            if not preludes:
                continue
            
            # Create a separate record for each prelude played
            for prelude in preludes:
                # Get ELO data
                elo_data = player_data.get('elo_data')
                elo_change = None
                elo_rating = None
                if elo_data and isinstance(elo_data, dict):
                    elo_change = elo_data.get('game_rank_change')
                    elo_rating = elo_data.get('game_rank')
                
                prelude_data = {
                    'prelude': prelude,
                    'player_id': player_id,
                    'player_name': player_data.get('player_name', 'Unknown'),
                    'corporation': normalize_corporation_name(player_data.get('corporation', 'Unknown')),
                    'final_vp': player_data.get('final_vp', 0),
                    'won_game': player_id == winner_id,
                    'elo_change': elo_change,
                    'elo_rating': elo_rating,
                    'replay_id': game_data.get('replay_id', 'unknown'),
                    'game_date': game_data.get('game_date', 'unknown')
                }
                prelude_data_list.append(prelude_data)
        
        return prelude_data_list
        
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

def analyze_prelude_win_rates(data_dir):
    """
    Main analysis function that processes all games and calculates prelude win rate statistics.
    """
    print("Starting Prelude Win Rates analysis...")
    
    # Load prelude list
    prelude_set = load_prelude_list()
    if not prelude_set:
        print("Error: Could not load prelude list from preludes.json")
        return None, []
    
    print(f"Loaded {len(prelude_set)} prelude cards from preludes.json")
    
    # Find all game files
    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")
    
    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, []
    
    # Data structures for aggregation
    prelude_stats = defaultdict(lambda: {
        'total_played': 0,
        'total_wins': 0,
        'total_elo_change': 0,
        'total_elo_rating': 0,
        'elo_changes': [],  # For calculating statistics
        'elo_ratings': [],  # For calculating average ELO rating
        'play_instances': []  # For detailed tracking
    })
    
    all_prelude_data = []
    total_games_processed = 0
    total_prelude_instances = 0
    
    # Process each game file
    for i, game_file in enumerate(game_files):
        prelude_data_list = process_game_for_prelude_data(game_file, prelude_set)
        
        if prelude_data_list:
            total_games_processed += 1
            
            # Process each prelude from this game
            for prelude_data in prelude_data_list:
                prelude = prelude_data['prelude']
                won_game = prelude_data['won_game']
                elo_change = prelude_data['elo_change']
                elo_rating = prelude_data['elo_rating']
                
                # Update prelude statistics
                prelude_stats[prelude]['total_played'] += 1
                if won_game:
                    prelude_stats[prelude]['total_wins'] += 1
                
                # Update ELO statistics if available
                if elo_change is not None:
                    prelude_stats[prelude]['total_elo_change'] += elo_change
                    prelude_stats[prelude]['elo_changes'].append(elo_change)
                
                if elo_rating is not None:
                    prelude_stats[prelude]['total_elo_rating'] += elo_rating
                    prelude_stats[prelude]['elo_ratings'].append(elo_rating)
                
                prelude_stats[prelude]['play_instances'].append(prelude_data)
                
                # Add to overall data
                all_prelude_data.append(prelude_data)
                total_prelude_instances += 1
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} games...")
    
    print(f"\nAnalysis complete!")
    print(f"Games processed: {total_games_processed}")
    print(f"Total prelude instances: {total_prelude_instances}")
    print(f"Unique preludes: {len(prelude_stats)}")
    
    # Calculate final statistics for each prelude
    prelude_results = {}
    for prelude, stats in prelude_stats.items():
        win_rate = stats['total_wins'] / stats['total_played'] if stats['total_played'] > 0 else 0
        
        # Calculate ELO statistics
        elo_changes = stats['elo_changes']
        elo_ratings = stats['elo_ratings']
        avg_elo_change = stats['total_elo_change'] / len(elo_changes) if elo_changes else 0
        avg_elo_rating = stats['total_elo_rating'] / len(elo_ratings) if elo_ratings else 0
        min_elo_change = min(elo_changes) if elo_changes else 0
        max_elo_change = max(elo_changes) if elo_changes else 0
        
        prelude_results[prelude] = {
            'prelude': prelude,
            'total_played': stats['total_played'],
            'total_wins': stats['total_wins'],
            'win_rate': win_rate,
            'total_elo_change': stats['total_elo_change'],
            'avg_elo_change': avg_elo_change,
            'avg_elo_rating': avg_elo_rating,
            'min_elo_change': min_elo_change,
            'max_elo_change': max_elo_change,
            'elo_instances': len(elo_changes),
            'elo_rating_instances': len(elo_ratings),
            'play_instances': stats['play_instances']
        }
    
    return prelude_results, all_prelude_data

def display_results(prelude_results):
    """Display analysis results."""
    if not prelude_results:
        print("No results to display.")
        return
    
    print("\n" + "="*110)
    print("PRELUDE WIN RATES AND ELO ANALYSIS RESULTS")
    print("="*110)
    print("Win rate = Games won (1st place) / Total games where prelude was played")
    print("Average ELO change shows performance impact of each prelude")
    print("="*110)
    
    # Sort preludes by average ELO change (descending)
    sorted_preludes = sorted(prelude_results.items(), 
                            key=lambda x: x[1]['avg_elo_change'], 
                            reverse=True)
    
    print(f"\n{'Rank':<4} {'Prelude':<25} {'Played':<7} {'Wins':<6} {'Win Rate':<9} {'Avg ELO Δ':<9} {'Avg ELO':<8} {'ELO Data':<8}")
    print("-" * 120)
    
    for rank, (prelude, stats) in enumerate(sorted_preludes, 1):
        print(f"{rank:<4} {prelude:<25} {stats['total_played']:<7} "
              f"{stats['total_wins']:<6} {stats['win_rate']*100:<9.1f}% "
              f"{stats['avg_elo_change']:<9.2f} {stats['avg_elo_rating']:<8.0f} {stats['elo_instances']:<8}")
    
    # Calculate overall statistics
    total_played = sum(stats['total_played'] for stats in prelude_results.values())
    total_wins = sum(stats['total_wins'] for stats in prelude_results.values())
    overall_win_rate = total_wins / total_played if total_played > 0 else 0
    
    print(f"\n{'='*90}")
    print(f"SUMMARY STATISTICS:")
    print(f"Total prelude instances: {total_played}")
    print(f"Total wins with preludes: {total_wins}")
    print(f"Overall win rate with preludes: {overall_win_rate*100:.1f}%")
    print(f"Best prelude: {sorted_preludes[0][0]} ({sorted_preludes[0][1]['win_rate']*100:.1f}%)")
    print(f"Worst prelude: {sorted_preludes[-1][0]} ({sorted_preludes[-1][1]['win_rate']*100:.1f}%)")
    print(f"{'='*90}")

def save_detailed_results_to_csv(all_prelude_data, output_file):
    """Save detailed game-by-game prelude results to a CSV file."""
    if not all_prelude_data:
        print("No detailed results to save.")
        return
    
    try:
        fieldnames = ['prelude', 'player_id', 'player_name', 'corporation', 
                     'final_vp', 'won_game', 'elo_change', 'elo_rating', 'replay_id', 'game_date']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by prelude, then by game_date
            sorted_results = sorted(all_prelude_data, 
                                  key=lambda x: (x['prelude'], x['game_date']))
            
            for result in sorted_results:
                writer.writerow(result)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving detailed CSV file: {e}")

def save_prelude_summary_to_csv(prelude_results, output_file):
    """Save prelude summary statistics to a CSV file."""
    if not prelude_results:
        print("No prelude summary to save.")
        return
    
    try:
        fieldnames = ['prelude', 'total_played', 'total_wins', 'win_rate', 
                     'total_elo_change', 'avg_elo_change', 'avg_elo_rating', 'min_elo_change', 
                     'max_elo_change', 'elo_instances', 'elo_rating_instances']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by average ELO change (descending)
            sorted_preludes = sorted(prelude_results.items(), 
                                   key=lambda x: x[1]['avg_elo_change'], 
                                   reverse=True)
            
            for prelude, stats in sorted_preludes:
                row = {
                    'prelude': prelude,
                    'total_played': stats['total_played'],
                    'total_wins': stats['total_wins'],
                    'win_rate': round(stats['win_rate'], 4),
                    'total_elo_change': stats['total_elo_change'],
                    'avg_elo_change': round(stats['avg_elo_change'], 4),
                    'avg_elo_rating': round(stats['avg_elo_rating'], 1),
                    'min_elo_change': stats['min_elo_change'],
                    'max_elo_change': stats['max_elo_change'],
                    'elo_instances': stats['elo_instances'],
                    'elo_rating_instances': stats['elo_rating_instances']
                }
                writer.writerow(row)
        
        print(f"Prelude summary saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving prelude summary CSV file: {e}")

def plot_prelude_elo_histograms(prelude_results, output_dir, min_games=10):
    """
    Plot histograms showing ELO gain distribution for each prelude.
    
    Args:
        prelude_results: Dictionary containing prelude statistics
        output_dir: Directory to save histogram plots
        min_games: Minimum number of games required to generate a histogram
    """
    if not prelude_results:
        print("No prelude results to plot.")
        return
    
    # Filter preludes with sufficient data
    preludes_to_plot = {
        prelude: stats for prelude, stats in prelude_results.items() 
        if stats['total_played'] >= min_games and stats['elo_instances'] >= min_games
    }
    
    if not preludes_to_plot:
        print(f"No preludes have at least {min_games} games with ELO data. Skipping histogram generation.")
        return
    
    print(f"\nGenerating ELO distribution histograms for {len(preludes_to_plot)} preludes...")
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Determine overall ELO range for consistent binning
    all_elo_changes = []
    for stats in preludes_to_plot.values():
        all_elo_changes.extend([data['elo_change'] for data in stats['play_instances'] if data['elo_change'] is not None])
    
    if not all_elo_changes:
        print("No ELO change data found.")
        return
    
    min_elo = min(all_elo_changes)
    max_elo = max(all_elo_changes)
    
    # Create bins with 2 ELO point intervals
    bin_width = 2
    bin_start = int(min_elo // bin_width) * bin_width - bin_width
    bin_end = int(max_elo // bin_width) * bin_width + bin_width * 2
    bins = np.arange(bin_start, bin_end + bin_width, bin_width)
    
    print(f"Using ELO range: {bin_start} to {bin_end} with {bin_width}-point bins")
    
    # Sort preludes by average ELO change for consistent ordering
    sorted_preludes = sorted(preludes_to_plot.items(), 
                           key=lambda x: x[1]['avg_elo_change'], 
                           reverse=True)
    
    # Generate histogram for each prelude
    for prelude, stats in sorted_preludes:
        elo_changes = [data['elo_change'] for data in stats['play_instances'] if data['elo_change'] is not None]
        
        if not elo_changes:
            continue
        
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
        plt.title(f'ELO Gain Distribution - {prelude}\n'
                 f'({stats["total_played"]} games, Win Rate: {stats["win_rate"]*100:.1f}%, Avg ELO: {stats["avg_elo_rating"]:.0f})', 
                 fontsize=16, fontweight='bold')
        plt.xlabel('ELO Change', fontsize=14)
        plt.ylabel('Frequency', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=12)
        
        # Add statistics text box
        stats_text = f'Min: {stats["min_elo_change"]}\n' \
                    f'Max: {stats["max_elo_change"]}\n' \
                    f'Avg: {avg_elo:.2f}\n' \
                    f'Games: {stats["total_played"]}\n' \
                    f'ELO Data: {stats["elo_instances"]}'
        
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                fontsize=11, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Set x-axis limits with some padding
        plt.xlim(bin_start, bin_end)
        
        # Improve layout
        plt.tight_layout()
        
        # Save the plot
        safe_prelude_name = prelude.replace(' ', '_').replace('/', '_').replace('-', '_')
        filename = f'prelude_elo_histogram_{safe_prelude_name}.png'
        filepath = output_path / filename
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved histogram for {prelude}: {filename}")
    
    print(f"\nHistogram generation complete! {len(sorted_preludes)} plots saved to {output_path}")

def main():
    """Main function to run the Prelude Win Rates analysis."""
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    output_dir = script_dir / "data"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    detailed_output_file = output_dir / "prelude_win_rates_detailed.csv"
    summary_output_file = output_dir / "prelude_win_rates_summary.csv"
    
    print("Terraforming Mars - Prelude Win Rates Analysis")
    print("=" * 50)
    
    # Run the analysis
    prelude_results, all_prelude_data = analyze_prelude_win_rates(data_dir)
    
    if prelude_results:
        # Display results
        display_results(prelude_results)
        
        # Save to CSV files
        save_detailed_results_to_csv(all_prelude_data, detailed_output_file)
        save_prelude_summary_to_csv(prelude_results, summary_output_file)
        
        # Generate ELO distribution histograms
        plot_prelude_elo_histograms(prelude_results, output_dir, min_games=10)
        
        print(f"\nAnalysis complete! Check the CSV files and histogram plots in {output_dir} for detailed data.")
    else:
        print("No data found to analyze.")

if __name__ == "__main__":
    main()
