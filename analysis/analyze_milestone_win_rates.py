#!/usr/bin/env python3
"""
Analyze win rates per milestone claimed in Terraforming Mars games.

This script processes all parsed game files to calculate the win rate for each milestone.
Win rate is defined as the percentage of games won (1st place by final VP) when a specific
milestone was claimed by the player.

When a player claims multiple milestones in a single game, each milestone is counted
as a separate data point for analysis.
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

def process_game_for_milestone_data(file_path):
    """
    Process a single game file to extract milestone claim data and determine winner.
    Returns list of milestone data dictionaries or empty list if processing fails.
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
        
        milestone_data_list = []
        
        # Extract milestone data for each player
        for player_id, player_data in players.items():
            milestones_claimed = player_data.get('milestones_claimed', [])
            
            # Skip players who didn't claim any milestones
            if not milestones_claimed:
                continue
            
            # Create a separate record for each milestone claimed
            for milestone in milestones_claimed:
                milestone_data = {
                    'milestone': milestone,
                    'player_id': player_id,
                    'player_name': player_data.get('player_name', 'Unknown'),
                    'corporation': player_data.get('corporation', 'Unknown'),
                    'final_vp': player_data.get('final_vp', 0),
                    'won_game': player_id == winner_id,
                    'replay_id': game_data.get('replay_id', 'unknown'),
                    'game_date': game_data.get('game_date', 'unknown')
                }
                milestone_data_list.append(milestone_data)
        
        return milestone_data_list
        
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

def analyze_milestone_win_rates(data_dir):
    """
    Main analysis function that processes all games and calculates milestone win rate statistics.
    """
    print("Starting Milestone Win Rates analysis...")
    
    # Find all game files
    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")
    
    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, []
    
    # Data structures for aggregation
    milestone_stats = defaultdict(lambda: {
        'total_claims': 0,
        'total_wins': 0,
        'claim_instances': []  # For detailed tracking
    })
    
    all_milestone_data = []
    total_games_processed = 0
    total_milestone_instances = 0
    
    # Process each game file
    for i, game_file in enumerate(game_files):
        milestone_data_list = process_game_for_milestone_data(game_file)
        
        if milestone_data_list:
            total_games_processed += 1
            
            # Process each milestone claim from this game
            for milestone_data in milestone_data_list:
                milestone = milestone_data['milestone']
                won_game = milestone_data['won_game']
                
                # Update milestone statistics
                milestone_stats[milestone]['total_claims'] += 1
                if won_game:
                    milestone_stats[milestone]['total_wins'] += 1
                milestone_stats[milestone]['claim_instances'].append(milestone_data)
                
                # Add to overall data
                all_milestone_data.append(milestone_data)
                total_milestone_instances += 1
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} games...")
    
    print(f"\nAnalysis complete!")
    print(f"Games processed: {total_games_processed}")
    print(f"Total milestone instances: {total_milestone_instances}")
    print(f"Unique milestones: {len(milestone_stats)}")
    
    # Calculate final statistics for each milestone
    milestone_results = {}
    for milestone, stats in milestone_stats.items():
        win_rate = stats['total_wins'] / stats['total_claims'] if stats['total_claims'] > 0 else 0
        
        milestone_results[milestone] = {
            'milestone': milestone,
            'total_claims': stats['total_claims'],
            'total_wins': stats['total_wins'],
            'win_rate': win_rate,
            'claim_instances': stats['claim_instances']
        }
    
    return milestone_results, all_milestone_data

def display_results(milestone_results):
    """Display analysis results."""
    if not milestone_results:
        print("No results to display.")
        return
    
    print("\n" + "="*80)
    print("MILESTONE WIN RATES ANALYSIS RESULTS")
    print("="*80)
    print("Win rate = Games won (1st place) / Total games where milestone was claimed")
    print("Higher percentages indicate milestones associated with winning games")
    print("="*80)
    
    # Sort milestones by win rate (descending)
    sorted_milestones = sorted(milestone_results.items(), 
                              key=lambda x: x[1]['win_rate'], 
                              reverse=True)
    
    print(f"\n{'Rank':<4} {'Milestone':<15} {'Claims':<7} {'Wins':<6} {'Win Rate':<9}")
    print("-" * 80)
    
    for rank, (milestone, stats) in enumerate(sorted_milestones, 1):
        print(f"{rank:<4} {milestone:<15} {stats['total_claims']:<7} "
              f"{stats['total_wins']:<6} {stats['win_rate']*100:<9.1f}%")
    
    # Calculate overall statistics
    total_claims = sum(stats['total_claims'] for stats in milestone_results.values())
    total_wins = sum(stats['total_wins'] for stats in milestone_results.values())
    overall_win_rate = total_wins / total_claims if total_claims > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"SUMMARY STATISTICS:")
    print(f"Total milestone claims: {total_claims}")
    print(f"Total wins with milestones: {total_wins}")
    print(f"Overall win rate with milestones: {overall_win_rate*100:.1f}%")
    print(f"Best milestone: {sorted_milestones[0][0]} ({sorted_milestones[0][1]['win_rate']*100:.1f}%)")
    print(f"Worst milestone: {sorted_milestones[-1][0]} ({sorted_milestones[-1][1]['win_rate']*100:.1f}%)")
    print(f"{'='*80}")

def save_detailed_results_to_csv(all_milestone_data, output_file):
    """Save detailed game-by-game milestone results to a CSV file."""
    if not all_milestone_data:
        print("No detailed results to save.")
        return
    
    try:
        fieldnames = ['milestone', 'player_id', 'player_name', 'corporation', 
                     'final_vp', 'won_game', 'replay_id', 'game_date']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by milestone, then by game_date
            sorted_results = sorted(all_milestone_data, 
                                  key=lambda x: (x['milestone'], x['game_date']))
            
            for result in sorted_results:
                writer.writerow(result)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving detailed CSV file: {e}")

def save_milestone_summary_to_csv(milestone_results, output_file):
    """Save milestone summary statistics to a CSV file."""
    if not milestone_results:
        print("No milestone summary to save.")
        return
    
    try:
        fieldnames = ['milestone', 'total_claims', 'total_wins', 'win_rate']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by win rate (descending)
            sorted_milestones = sorted(milestone_results.items(), 
                                     key=lambda x: x[1]['win_rate'], 
                                     reverse=True)
            
            for milestone, stats in sorted_milestones:
                row = {
                    'milestone': milestone,
                    'total_claims': stats['total_claims'],
                    'total_wins': stats['total_wins'],
                    'win_rate': round(stats['win_rate'], 4)
                }
                writer.writerow(row)
        
        print(f"Milestone summary saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving milestone summary CSV file: {e}")

def main():
    """Main function to run the Milestone Win Rates analysis."""
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    detailed_output_file = script_dir / "milestone_win_rates_detailed.csv"
    summary_output_file = script_dir / "milestone_win_rates_summary.csv"
    
    print("Terraforming Mars - Milestone Win Rates Analysis")
    print("=" * 50)
    
    # Run the analysis
    milestone_results, all_milestone_data = analyze_milestone_win_rates(data_dir)
    
    if milestone_results:
        # Display results
        display_results(milestone_results)
        
        # Save to CSV files
        save_detailed_results_to_csv(all_milestone_data, detailed_output_file)
        save_milestone_summary_to_csv(milestone_results, summary_output_file)
        
        print(f"\nAnalysis complete! Check the CSV files for detailed data.")
    else:
        print("No data found to analyze.")

if __name__ == "__main__":
    main()
