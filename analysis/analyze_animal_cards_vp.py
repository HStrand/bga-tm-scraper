#!/usr/bin/env python3
"""
Analyze average VP scored on animal cards across all Terraforming Mars games.

This script processes all parsed game files to calculate comprehensive statistics
about VP scored from animal cards, including average VP per card type, frequency
of play, and distribution analysis.

VP data comes from the final_state.player_vp[player_id].details.cards[card_name].vp field.
Only includes cards that were actually played (exist in the cards dictionary).
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
import csv
import statistics

# Animal cards to analyze
ANIMAL_CARDS = [
    "Predators",
    "Fish", 
    "Small Animals",
    "Birds",
    "Ecological Zone",
    "Herbivores",
    "Pets",
    "Livestock"
]

def process_game_for_animal_vp(file_path):
    """
    Process a single game file to extract animal card VP data for all players.
    Returns list of animal card VP data or empty list if processing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        # Check if final_state exists
        final_state = game_data["moves"][-1]["game_state"]
        if not final_state:
            print(f"Warning: No final_state found in {file_path}")
            return []
        
        # Check if player_vp exists
        player_vp = final_state.get('player_vp')
        if not player_vp:
            print(f"Warning: No player_vp found in final_state in {file_path}")
            return []
        
        animal_vp_data = []
        
        # Extract animal card VP for each player
        for player_id, vp_data in player_vp.items():
            # Get player info from the main players section
            players = game_data.get('players', {})
            player_info = players.get(player_id, {})
            player_name = player_info.get('player_name', 'Unknown')
            corporation = player_info.get('corporation', 'Unknown')
            
            # Check if details exist
            details = vp_data.get('details')
            if not details:
                print(f"Warning: No details found for player {player_id} in {file_path}")
                continue
            
            # Check if cards exist
            cards = details.get('cards')
            if not cards:
                print(f"Warning: No cards found for player {player_id} in {file_path}")
                continue
            
            # Process each animal card type
            for animal_card in ANIMAL_CARDS:
                if animal_card in cards:
                    # Extract VP from the nested structure
                    card_data = cards[animal_card]
                    if isinstance(card_data, dict) and 'vp' in card_data:
                        vp_value = card_data['vp']
                        
                        # Add to results (include even if VP is 0, since card was played)
                        animal_vp_data.append({
                            'card_name': animal_card,
                            'vp': vp_value,
                            'player_id': player_id,
                            'player_name': player_name,
                            'corporation': corporation,
                            'replay_id': game_data.get('replay_id', 'unknown'),
                            'game_date': game_data.get('game_date', 'unknown')
                        })
                    else:
                        print(f"Warning: Invalid card data structure for {animal_card} in player {player_id} in {file_path}")
        
        return animal_vp_data
        
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
        if "86296239" in str(player_dir):
            continue

        if player_dir.is_dir() and player_dir.name.isdigit():
            for game_file in player_dir.glob("*.json"):
                game_files.append(game_file)
    
    return game_files

def analyze_animal_cards_vp(data_dir):
    """
    Main analysis function that processes all games and calculates animal card VP statistics.
    """
    print("Starting Animal Cards VP analysis...")
    
    # Find all game files
    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")
    
    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, []
    
    # Data structures for aggregation
    card_stats = defaultdict(lambda: {
        'total_vp': 0,
        'times_played': 0,
        'vp_values': [],  # For calculating statistics
        'instances': []   # For detailed tracking
    })
    
    all_animal_data = []
    total_games_processed = 0
    total_animal_instances = 0
    
    # Process each game file
    for i, game_file in enumerate(game_files):
        animal_vp_data = process_game_for_animal_vp(game_file)
        
        if animal_vp_data:
            total_games_processed += 1
            
            # Process each animal card instance from this game
            for animal_data in animal_vp_data:
                card_name = animal_data['card_name']
                vp_value = animal_data['vp']
                
                # Update card statistics
                card_stats[card_name]['total_vp'] += vp_value
                card_stats[card_name]['times_played'] += 1
                card_stats[card_name]['vp_values'].append(vp_value)
                card_stats[card_name]['instances'].append(animal_data)
                
                # Add to overall data
                all_animal_data.append(animal_data)
                total_animal_instances += 1
        
        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} games...")
    
    print(f"\nAnalysis complete!")
    print(f"Games processed: {total_games_processed}")
    print(f"Total animal card instances: {total_animal_instances}")
    print(f"Animal card types found: {len(card_stats)}")
    
    # Calculate final statistics for each card type
    card_results = {}
    for card_name, stats in card_stats.items():
        if stats['times_played'] > 0:
            avg_vp = stats['total_vp'] / stats['times_played']
            
            # Calculate additional statistics
            vp_values = stats['vp_values']
            min_vp = min(vp_values)
            max_vp = max(vp_values)
            std_dev = statistics.stdev(vp_values) if len(vp_values) > 1 else 0
            
            card_results[card_name] = {
                'card_name': card_name,
                'times_played': stats['times_played'],
                'total_vp': stats['total_vp'],
                'avg_vp': avg_vp,
                'min_vp': min_vp,
                'max_vp': max_vp,
                'std_dev': std_dev,
                'instances': stats['instances']
            }
    
    return card_results, all_animal_data

def display_results(card_results):
    """Display analysis results."""
    if not card_results:
        print("No results to display.")
        return
    
    print("\n" + "="*100)
    print("ANIMAL CARDS VP ANALYSIS RESULTS")
    print("="*100)
    print("VP statistics for animal cards across all games")
    print("Only includes games where each card was actually played")
    print("="*100)
    
    # Sort cards by average VP (descending)
    sorted_cards = sorted(card_results.items(), 
                         key=lambda x: x[1]['avg_vp'], 
                         reverse=True)
    
    print(f"\n{'Rank':<4} {'Card Name':<18} {'Times Played':<12} {'Avg VP':<8} {'Total VP':<9} {'Min':<4} {'Max':<4} {'Std Dev':<8}")
    print("-" * 100)
    
    for rank, (card_name, stats) in enumerate(sorted_cards, 1):
        print(f"{rank:<4} {card_name:<18} {stats['times_played']:<12} "
              f"{stats['avg_vp']:<8.2f} {stats['total_vp']:<9} "
              f"{stats['min_vp']:<4} {stats['max_vp']:<4} "
              f"{stats['std_dev']:<8.2f}")
    
    # Calculate overall statistics
    total_instances = sum(stats['times_played'] for stats in card_results.values())
    total_vp = sum(stats['total_vp'] for stats in card_results.values())
    overall_avg = total_vp / total_instances if total_instances > 0 else 0
    
    print(f"\n{'='*100}")
    print(f"SUMMARY STATISTICS:")
    print(f"Total animal card instances: {total_instances}")
    print(f"Total VP from animal cards: {total_vp}")
    print(f"Overall average VP per animal card: {overall_avg:.3f}")
    print(f"Most valuable (avg VP): {sorted_cards[0][0]} ({sorted_cards[0][1]['avg_vp']:.2f})")
    print(f"Most popular (times played): {max(card_results.items(), key=lambda x: x[1]['times_played'])[0]} ({max(card_results.items(), key=lambda x: x[1]['times_played'])[1]['times_played']} times)")
    print(f"{'='*100}")

def save_detailed_results_to_csv(all_animal_data, output_file):
    """Save detailed game-by-game results to a CSV file."""
    if not all_animal_data:
        print("No detailed results to save.")
        return
    
    try:
        fieldnames = ['card_name', 'vp', 'player_id', 'player_name', 
                     'corporation', 'replay_id', 'game_date']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by card name, then by VP (descending)
            sorted_results = sorted(all_animal_data, 
                                  key=lambda x: (x['card_name'], -x['vp']))
            
            for result in sorted_results:
                writer.writerow(result)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving detailed CSV file: {e}")

def save_card_summary_to_csv(card_results, output_file):
    """Save card summary statistics to a CSV file."""
    if not card_results:
        print("No card summary to save.")
        return
    
    try:
        fieldnames = ['card_name', 'times_played', 'total_vp', 'avg_vp', 
                     'min_vp', 'max_vp', 'std_dev']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by average VP (descending)
            sorted_cards = sorted(card_results.items(), 
                                key=lambda x: x[1]['avg_vp'], 
                                reverse=True)
            
            for card_name, stats in sorted_cards:
                row = {
                    'card_name': card_name,
                    'times_played': stats['times_played'],
                    'total_vp': stats['total_vp'],
                    'avg_vp': round(stats['avg_vp'], 4),
                    'min_vp': stats['min_vp'],
                    'max_vp': stats['max_vp'],
                    'std_dev': round(stats['std_dev'], 4)
                }
                writer.writerow(row)
        
        print(f"Card summary saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving card summary CSV file: {e}")

def main():
    """Main function to run the Animal Cards VP analysis."""
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    detailed_output_file = script_dir / "animal_cards_vp_detailed.csv"
    summary_output_file = script_dir / "animal_cards_vp_summary.csv"
    
    print("Terraforming Mars - Animal Cards VP Analysis")
    print("=" * 50)
    
    # Run the analysis
    card_results, all_animal_data = analyze_animal_cards_vp(data_dir)
    
    if card_results:
        # Display results
        display_results(card_results)
        
        # Save to CSV files
        save_detailed_results_to_csv(all_animal_data, detailed_output_file)
        save_card_summary_to_csv(card_results, summary_output_file)
        
        print(f"\nAnalysis complete! Check the CSV files for detailed data.")
    else:
        print("No data found to analyze.")

if __name__ == "__main__":
    main()
