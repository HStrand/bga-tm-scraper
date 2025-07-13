#!/usr/bin/env python3
"""
Analyze win rates per award won in Terraforming Mars games.

This script processes all parsed game files to calculate the win rate for each award.
Win rate is defined as the percentage of games won (1st place by final VP) when a specific
award was won (place: 1) by the player.

Awards are found in the final_state.player_vp[player_id].details.awards structure,
where winning an award means having "place": 1 for that award.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
import csv

def determine_game_winner(players):
    """
    Determine the winner of a game based on highest final_vp.
    Returns the player_id of the winner, or None if there's a tie or no valid data.
    """
    if not players:
        return None
    
    max_vp = -1
    winner_id = None
    tie_count = 0
    
    for player_id, player_data in players.items():
        final_vp = player_data.get('final_vp', 0)
        
        if final_vp > max_vp:
            max_vp = final_vp
            winner_id = player_id
            tie_count = 1
        elif final_vp == max_vp and final_vp > 0:
            tie_count += 1
    
    # Return None if there's a tie (shouldn't happen in TM, but being safe)
    if tie_count > 1:
        return None
    
    return winner_id

def process_game_for_award_data(file_path):
    """
    Process a single game file to extract award win data and determine winner.
    Returns list of award data dictionaries or empty list if processing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        # Get all players from the game
        players = game_data.get('players', {})
        if not players:
            print(f"Warning: No players found in {file_path}")
            return []
        
        # Determine the winner
        winner_id = determine_game_winner(players)
        if not winner_id:
            print(f"Warning: Could not determine winner in {file_path}")
            return []
        
        # Get final_state data for award information
        final_state = game_data.get('final_state', {})
        player_vp = final_state.get('player_vp', {})
        
        if not player_vp:
            print(f"Warning: No final_state.player_vp found in {file_path}")
            return []
        
        award_data_list = []
        
        # Extract award data for each player
        for player_id, player_data in players.items():
            # Get award details from final_state
            if player_id not in player_vp:
                continue
            
            vp_details = player_vp[player_id].get('details', {})
            awards = vp_details.get('awards', {})
            
            if not awards:
                continue
            
            # Check each award to see if this player won it (place: 1)
            for award_name, award_info in awards.items():
                if award_info.get('place') == 1:
                    # This player won this award
                    award_data = {
                        'award': award_name,
                        'player_id': player_id,
                        'player_name': player_data.get('player_name', 'Unknown'),
                        'corporation': player_data.get('corporation', 'Unknown'),
                        'final_vp': player_data.get('final_vp', 0),
                        'award_vp': award_info.get('vp', 0),
                        'award_counter': award_info.get('counter', 0),
                        'won_game': player_id == winner_id,
                        'replay_id': game_data.get('replay_id', 'unknown'),
                        'game_date': game_data.get('game_date', 'unknown')
                    }
                    award_data_list.append(award_data)
        
        return award_data_list
        
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

def analyze_award_win_rates(data_dir):
    """
    Main analysis function that processes all games and calculates award win rate statistics.
    """
    print("Starting Award Win Rates analysis...")
    
    # Find all game files
    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")
    
    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, []
    
    # Data structures for aggregation
    award_stats = defaultdict(lambda: {
        'total_wins': 0,
        'total_game_wins': 0,
        'win_instances': []  # For detailed tracking
    })
    
    all_award_data = []
    total_games_processed = 0
    total_award_instances = 0
    
    # Process each game file
    for i, game_file in enumerate(game_files):
        award_data_list = process_game_for_award_data(game_file)
        
        if award_data_list:
            total_games_processed += 1
            
            # Process each award win from this game
            for award_data in award_data_list:
                award = award_data['award']
                won_game = award_data['won_game']
                
                # Update award statistics
                award_stats[award]['total_wins'] += 1
                if won_game:
                    award_stats[award]['total_game_wins'] += 1
                award_stats[award]['win_instances'].append(award_data)
                
                # Add to overall data
                all_award_data.append(award_data)
                total_award_instances += 1
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} games...")
    
    print(f"\nAnalysis complete!")
    print(f"Games processed: {total_games_processed}")
    print(f"Total award instances: {total_award_instances}")
    print(f"Unique awards: {len(award_stats)}")
    
    # Calculate final statistics for each award
    award_results = {}
    for award, stats in award_stats.items():
        win_rate = stats['total_game_wins'] / stats['total_wins'] if stats['total_wins'] > 0 else 0
        
        award_results[award] = {
            'award': award,
            'total_wins': stats['total_wins'],
            'total_game_wins': stats['total_game_wins'],
            'win_rate': win_rate,
            'win_instances': stats['win_instances']
        }
    
    return award_results, all_award_data

def display_results(award_results):
    """Display analysis results."""
    if not award_results:
        print("No results to display.")
        return
    
    print("\n" + "="*80)
    print("AWARD WIN RATES ANALYSIS RESULTS")
    print("="*80)
    print("Win rate = Games won (1st place) / Total times award was won (1st place)")
    print("Higher percentages indicate awards associated with winning games")
    print("="*80)
    
    # Sort awards by win rate (descending)
    sorted_awards = sorted(award_results.items(), 
                          key=lambda x: x[1]['win_rate'], 
                          reverse=True)
    
    print(f"\n{'Rank':<4} {'Award':<15} {'Award Wins':<11} {'Game Wins':<10} {'Win Rate':<9}")
    print("-" * 80)
    
    for rank, (award, stats) in enumerate(sorted_awards, 1):
        print(f"{rank:<4} {award:<15} {stats['total_wins']:<11} "
              f"{stats['total_game_wins']:<10} {stats['win_rate']*100:<9.1f}%")
    
    # Calculate overall statistics
    total_award_wins = sum(stats['total_wins'] for stats in award_results.values())
    total_game_wins = sum(stats['total_game_wins'] for stats in award_results.values())
    overall_win_rate = total_game_wins / total_award_wins if total_award_wins > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"SUMMARY STATISTICS:")
    print(f"Total award wins: {total_award_wins}")
    print(f"Total game wins with awards: {total_game_wins}")
    print(f"Overall win rate with awards: {overall_win_rate*100:.1f}%")
    print(f"Best award: {sorted_awards[0][0]} ({sorted_awards[0][1]['win_rate']*100:.1f}%)")
    print(f"Worst award: {sorted_awards[-1][0]} ({sorted_awards[-1][1]['win_rate']*100:.1f}%)")
    print(f"{'='*80}")

def save_detailed_results_to_csv(all_award_data, output_file):
    """Save detailed game-by-game award results to a CSV file."""
    if not all_award_data:
        print("No detailed results to save.")
        return
    
    try:
        fieldnames = ['award', 'player_id', 'player_name', 'corporation', 
                     'final_vp', 'award_vp', 'award_counter', 'won_game', 
                     'replay_id', 'game_date']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by award, then by game_date
            sorted_results = sorted(all_award_data, 
                                  key=lambda x: (x['award'], x['game_date']))
            
            for result in sorted_results:
                writer.writerow(result)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving detailed CSV file: {e}")

def save_award_summary_to_csv(award_results, output_file):
    """Save award summary statistics to a CSV file."""
    if not award_results:
        print("No award summary to save.")
        return
    
    try:
        fieldnames = ['award', 'total_wins', 'total_game_wins', 'win_rate']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by win rate (descending)
            sorted_awards = sorted(award_results.items(), 
                                 key=lambda x: x[1]['win_rate'], 
                                 reverse=True)
            
            for award, stats in sorted_awards:
                row = {
                    'award': award,
                    'total_wins': stats['total_wins'],
                    'total_game_wins': stats['total_game_wins'],
                    'win_rate': round(stats['win_rate'], 4)
                }
                writer.writerow(row)
        
        print(f"Award summary saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving award summary CSV file: {e}")

def main():
    """Main function to run the Award Win Rates analysis."""
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    detailed_output_file = script_dir / "award_win_rates_detailed.csv"
    summary_output_file = script_dir / "award_win_rates_summary.csv"
    
    print("Terraforming Mars - Award Win Rates Analysis")
    print("=" * 50)
    
    # Run the analysis
    award_results, all_award_data = analyze_award_win_rates(data_dir)
    
    if award_results:
        # Display results
        display_results(award_results)
        
        # Save to CSV files
        save_detailed_results_to_csv(all_award_data, detailed_output_file)
        save_award_summary_to_csv(award_results, summary_output_file)
        
        print(f"\nAnalysis complete! Check the CSV files for detailed data.")
    else:
        print("No data found to analyze.")

if __name__ == "__main__":
    main()
