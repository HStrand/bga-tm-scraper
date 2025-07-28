#!/usr/bin/env python3
"""
Analyze win rates for Ecology Experts + follow-up card combinations in Terraforming Mars games.

This script processes all parsed game files to calculate the win rate for each combination
of Ecology Experts prelude and the card played immediately after it (using EE's ability
to ignore global requirements).

The script identifies EE plays by looking for "Ecology Experts" in the cards_played array,
then finds the next card played by the same player in the game moves sequence.
Win rate is defined as the percentage of games won (1st place) when a specific
EE + card combination was played.
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

def find_ecology_experts_combinations(game_data, players):
    """
    Find all Ecology Experts + follow-up card combinations in the game.
    
    Args:
        game_data: Dictionary containing game information including moves
        players: Dictionary of player data
        
    Returns:
        List of combination data dictionaries
    """
    combinations = []
    moves = game_data.get('moves', [])
    
    if not moves:
        return combinations
    
    # Process moves to find EE plays and their follow-ups
    for i, move in enumerate(moves):
        # Check if this move is playing Ecology Experts
        if (move.get('action_type') == 'play_card' and 
            move.get('card_played') == 'Ecology Experts'):
            
            player_id = move.get('player_id')
            if not player_id:
                continue
            
            # Look for the next card played by the same player
            follow_up_card = None
            for j in range(i + 1, len(moves)):
                next_move = moves[j]
                if (next_move.get('player_id') == player_id and 
                    next_move.get('action_type') == 'play_card' and
                    next_move.get('card_played')):
                    follow_up_card = next_move.get('card_played')
                    break
            
            # If we found a follow-up card, record the combination
            if follow_up_card:
                player_data = players.get(player_id, {})
                
                # Get ELO data
                elo_data = player_data.get('elo_data')
                elo_change = None
                elo_rating = None
                if elo_data and isinstance(elo_data, dict):
                    elo_change = elo_data.get('game_rank_change')
                    elo_rating = elo_data.get('game_rank')
                
                combination_data = {
                    'combination': f"Ecology Experts + {follow_up_card}",
                    'ecology_experts': 'Ecology Experts',
                    'follow_up_card': follow_up_card,
                    'player_id': player_id,
                    'player_name': player_data.get('player_name', 'Unknown'),
                    'corporation': normalize_corporation_name(player_data.get('corporation', 'Unknown')),
                    'final_vp': player_data.get('final_vp', 0),
                    'elo_change': elo_change,
                    'elo_rating': elo_rating,
                    'replay_id': game_data.get('replay_id', 'unknown'),
                    'game_date': game_data.get('game_date', 'unknown')
                }
                combinations.append(combination_data)
    
    return combinations

def process_game_for_ee_combinations(file_path):
    """
    Process a single game file to extract Ecology Experts combination data.
    Returns list of combination data dictionaries or empty list if processing fails.
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
        
        # Find all EE combinations in this game
        combinations = find_ecology_experts_combinations(game_data, players)
        
        # Add winner information to each combination
        for combination in combinations:
            combination['won_game'] = combination['player_id'] == winner_id
        
        return combinations
        
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

def analyze_ee_combinations(data_dir):
    """
    Main analysis function that processes all games and calculates EE combination win rate statistics.
    """
    print("Starting Ecology Experts Combinations analysis...")
    
    # Find all game files
    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")
    
    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, []
    
    # Data structures for aggregation
    combination_stats = defaultdict(lambda: {
        'total_played': 0,
        'total_wins': 0,
        'total_elo_change': 0,
        'total_elo_rating': 0,
        'elo_changes': [],  # For calculating statistics
        'elo_ratings': [],  # For calculating average ELO rating
        'play_instances': []  # For detailed tracking
    })
    
    all_combination_data = []
    total_games_processed = 0
    total_ee_instances = 0
    
    # Process each game file
    for i, game_file in enumerate(game_files):
        combination_data_list = process_game_for_ee_combinations(game_file)
        
        if combination_data_list:
            total_games_processed += 1
            
            # Process each combination from this game
            for combination_data in combination_data_list:
                combination = combination_data['combination']
                won_game = combination_data['won_game']
                elo_change = combination_data['elo_change']
                elo_rating = combination_data['elo_rating']
                
                # Update combination statistics
                combination_stats[combination]['total_played'] += 1
                if won_game:
                    combination_stats[combination]['total_wins'] += 1
                
                # Update ELO statistics if available
                if elo_change is not None:
                    combination_stats[combination]['total_elo_change'] += elo_change
                    combination_stats[combination]['elo_changes'].append(elo_change)
                
                if elo_rating is not None:
                    combination_stats[combination]['total_elo_rating'] += elo_rating
                    combination_stats[combination]['elo_ratings'].append(elo_rating)
                
                combination_stats[combination]['play_instances'].append(combination_data)
                
                # Add to overall data
                all_combination_data.append(combination_data)
                total_ee_instances += 1
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} games...")
    
    print(f"\nAnalysis complete!")
    print(f"Games processed: {total_games_processed}")
    print(f"Total EE combination instances: {total_ee_instances}")
    print(f"Unique combinations: {len(combination_stats)}")
    
    # Calculate final statistics for each combination
    combination_results = {}
    for combination, stats in combination_stats.items():
        win_rate = stats['total_wins'] / stats['total_played'] if stats['total_played'] > 0 else 0
        
        # Calculate ELO statistics
        elo_changes = stats['elo_changes']
        elo_ratings = stats['elo_ratings']
        avg_elo_change = stats['total_elo_change'] / len(elo_changes) if elo_changes else 0
        avg_elo_rating = stats['total_elo_rating'] / len(elo_ratings) if elo_ratings else 0
        min_elo_change = min(elo_changes) if elo_changes else 0
        max_elo_change = max(elo_changes) if elo_changes else 0
        
        combination_results[combination] = {
            'combination': combination,
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
    
    return combination_results, all_combination_data

def display_results(combination_results, min_games=3):
    """Display analysis results, filtering by minimum games played."""
    if not combination_results:
        print("No results to display.")
        return
    
    # Filter combinations with sufficient data
    filtered_results = {
        combo: stats for combo, stats in combination_results.items() 
        if stats['total_played'] >= min_games
    }
    
    print("\n" + "="*130)
    print("ECOLOGY EXPERTS COMBINATION WIN RATES AND ELO ANALYSIS RESULTS")
    print("="*130)
    print("Win rate = Games won (1st place) / Total games where combination was played")
    print("Average ELO change shows performance impact of each combination")
    print(f"Showing combinations with at least {min_games} games played")
    print("="*130)
    
    if not filtered_results:
        print(f"No combinations have at least {min_games} games played.")
        return
    
    # Sort combinations by average ELO change (descending)
    sorted_combinations = sorted(filtered_results.items(), 
                               key=lambda x: x[1]['avg_elo_change'], 
                               reverse=True)
    
    print(f"\n{'Rank':<4} {'Combination':<45} {'Played':<7} {'Wins':<6} {'Win Rate':<9} {'Avg ELO Δ':<9} {'Avg ELO':<8} {'ELO Data':<8}")
    print("-" * 140)
    
    for rank, (combination, stats) in enumerate(sorted_combinations, 1):
        print(f"{rank:<4} {combination:<45} {stats['total_played']:<7} "
              f"{stats['total_wins']:<6} {stats['win_rate']*100:<9.1f}% "
              f"{stats['avg_elo_change']:<9.2f} {stats['avg_elo_rating']:<8.0f} {stats['elo_instances']:<8}")
    
    # Calculate overall statistics
    total_played = sum(stats['total_played'] for stats in filtered_results.values())
    total_wins = sum(stats['total_wins'] for stats in filtered_results.values())
    overall_win_rate = total_wins / total_played if total_played > 0 else 0
    
    print(f"\n{'='*100}")
    print(f"SUMMARY STATISTICS (combinations with {min_games}+ games):")
    print(f"Total combination instances: {total_played}")
    print(f"Total wins with combinations: {total_wins}")
    print(f"Overall win rate with combinations: {overall_win_rate*100:.1f}%")
    if sorted_combinations:
        print(f"Best combination: {sorted_combinations[0][0]} ({sorted_combinations[0][1]['win_rate']*100:.1f}%)")
        print(f"Worst combination: {sorted_combinations[-1][0]} ({sorted_combinations[-1][1]['win_rate']*100:.1f}%)")
    print(f"{'='*100}")

def save_detailed_results_to_csv(all_combination_data, output_file):
    """Save detailed game-by-game combination results to a CSV file."""
    if not all_combination_data:
        print("No detailed results to save.")
        return
    
    try:
        fieldnames = ['combination', 'ecology_experts', 'follow_up_card', 'player_id', 'player_name', 
                     'corporation', 'final_vp', 'won_game', 'elo_change', 'elo_rating', 'replay_id', 'game_date']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by combination, then by game_date
            sorted_results = sorted(all_combination_data, 
                                  key=lambda x: (x['combination'], x['game_date']))
            
            for result in sorted_results:
                writer.writerow(result)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving detailed CSV file: {e}")

def save_combination_summary_to_csv(combination_results, output_file, min_games=1):
    """Save combination summary statistics to a CSV file."""
    if not combination_results:
        print("No combination summary to save.")
        return
    
    try:
        fieldnames = ['combination', 'follow_up_card', 'total_played', 'total_wins', 'win_rate', 
                     'total_elo_change', 'avg_elo_change', 'avg_elo_rating', 'min_elo_change', 
                     'max_elo_change', 'elo_instances', 'elo_rating_instances']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Filter and sort by average ELO change (descending)
            filtered_combinations = {
                combo: stats for combo, stats in combination_results.items() 
                if stats['total_played'] >= min_games
            }
            
            sorted_combinations = sorted(filtered_combinations.items(), 
                                       key=lambda x: x[1]['avg_elo_change'], 
                                       reverse=True)
            
            for combination, stats in sorted_combinations:
                # Extract follow-up card name from combination
                follow_up_card = combination.replace('Ecology Experts + ', '')
                
                row = {
                    'combination': combination,
                    'follow_up_card': follow_up_card,
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
        
        print(f"Combination summary saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving combination summary CSV file: {e}")

def plot_combination_elo_histograms(combination_results, output_dir, min_games=5):
    """
    Plot histograms showing ELO gain distribution for each combination.
    
    Args:
        combination_results: Dictionary containing combination statistics
        output_dir: Directory to save histogram plots
        min_games: Minimum number of games required to generate a histogram
    """
    if not combination_results:
        print("No combination results to plot.")
        return
    
    # Filter combinations with sufficient data
    combinations_to_plot = {
        combo: stats for combo, stats in combination_results.items() 
        if stats['total_played'] >= min_games and stats['elo_instances'] >= min_games
    }
    
    if not combinations_to_plot:
        print(f"No combinations have at least {min_games} games with ELO data. Skipping histogram generation.")
        return
    
    print(f"\nGenerating ELO distribution histograms for {len(combinations_to_plot)} combinations...")
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Determine overall ELO range for consistent binning
    all_elo_changes = []
    for stats in combinations_to_plot.values():
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
    
    # Sort combinations by average ELO change for consistent ordering
    sorted_combinations = sorted(combinations_to_plot.items(), 
                               key=lambda x: x[1]['avg_elo_change'], 
                               reverse=True)
    
    # Generate histogram for each combination
    for combination, stats in sorted_combinations:
        elo_changes = [data['elo_change'] for data in stats['play_instances'] if data['elo_change'] is not None]
        
        if not elo_changes:
            continue
        
        # Create the plot
        plt.figure(figsize=(14, 8))
        
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
        plt.title(f'ELO Gain Distribution - {combination}\n'
                 f'({stats["total_played"]} games, Win Rate: {stats["win_rate"]*100:.1f}%, Avg ELO: {stats["avg_elo_rating"]:.0f})', 
                 fontsize=14, fontweight='bold')
        plt.xlabel('ELO Change', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10)
        
        # Add statistics text box
        stats_text = f'Min: {stats["min_elo_change"]}\n' \
                    f'Max: {stats["max_elo_change"]}\n' \
                    f'Avg: {avg_elo:.2f}\n' \
                    f'Games: {stats["total_played"]}\n' \
                    f'ELO Data: {stats["elo_instances"]}'
        
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                fontsize=10, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Set x-axis limits with some padding
        plt.xlim(bin_start, bin_end)
        
        # Improve layout
        plt.tight_layout()
        
        # Save the plot
        safe_combination_name = combination.replace(' ', '_').replace('/', '_').replace('-', '_').replace('+', 'plus')
        filename = f'ee_combination_elo_histogram_{safe_combination_name}.png'
        filepath = output_path / filename
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved histogram for {combination}: {filename}")
    
    print(f"\nHistogram generation complete! {len(sorted_combinations)} plots saved to {output_path}")

def main():
    """Main function to run the Ecology Experts Combinations analysis."""
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    output_dir = script_dir / "data"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    detailed_output_file = output_dir / "ecology_experts_combinations_detailed.csv"
    summary_output_file = output_dir / "ecology_experts_combinations_summary.csv"
    
    print("Terraforming Mars - Ecology Experts Combinations Analysis")
    print("=" * 60)
    
    # Run the analysis
    combination_results, all_combination_data = analyze_ee_combinations(data_dir)
    
    if combination_results:
        # Display results
        display_results(combination_results, min_games=3)
        
        # Save to CSV files
        save_detailed_results_to_csv(all_combination_data, detailed_output_file)
        save_combination_summary_to_csv(combination_results, summary_output_file, min_games=1)
        
        # Generate ELO distribution histograms
        plot_combination_elo_histograms(combination_results, output_dir, min_games=5)
        
        print(f"\nAnalysis complete! Check the CSV files and histogram plots in {output_dir} for detailed data.")
    else:
        print("No data found to analyze.")

if __name__ == "__main__":
    main()
