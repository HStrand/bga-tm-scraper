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

# VP values for animals stolen by Predators
STOLEN_ANIMAL_VP = {
    "Fish": 1,
    "Small Animals": 0.5,
    "Birds": 1,
    "Ecological Zone": 0.5,
    "Herbivores": 0.5,
    "Livestock": 1,
    "Penguins": 1  # Assuming Penguins is a custom card or expansion
}

PLANT_REDUCTION_CARDS = {
    "Fish": 1,
    "Birds": 2,
    "Small Animals": 1,
    "Herbivores": 1,
    "Livestock": 1
}

def calculate_plants_denied(moves, move_index, player_id, card_name, reduction_value, final_generation):
    """
    Calculate plants denied to self or opponents from a card play, considering generations.
    """
    plants_denied_opponent = 0
    plants_denied_self = 0

    # Get the generation the card was played
    card_play_move = moves[move_index]
    game_state = card_play_move.get('game_state')
    if not game_state:
        return 0, 0 # Cannot determine generation
        
    card_play_generation = game_state.get('generation')

    if card_play_generation is None:
        return 0, 0

    generations_affected = final_generation - card_play_generation + 1
    total_reduction = reduction_value * generations_affected

    if card_name == "Livestock":
        return 0, total_reduction

    # Search for the reduction effect in subsequent moves (with a lookahead limit)
    for i in range(move_index + 1, min(move_index + 10, len(moves))):
        subsequent_move = moves[i]
        if "reduces" in subsequent_move.get('description', ''):
            if subsequent_move.get('player_id') == player_id:
                plants_denied_self = total_reduction
            else:
                plants_denied_opponent = total_reduction
            break  # Found the first reduction, stop searching
    
    return plants_denied_opponent, plants_denied_self

def calculate_predators_stolen_vp(moves, player_id, game_data):
    """
    Calculate the VP stolen by a player using the Predators card.
    Returns (stolen_vp_from_opponent, stolen_vp_from_self).
    """
    stolen_vp_from_opponent = 0
    stolen_vp_from_self = 0
    player_name = None

    # First, find the player's name
    for move in moves:
        if move.get('player_id') == player_id:
            player_name = move.get('player_name')
            break
    
    if not player_name:
        return 0, 0

    # Get cards played by each player
    players = game_data.get('players', {})
    cards_played_by_player = {}
    for pid, player_info in players.items():
        cards_played = player_info.get('cards_played', [])
        cards_played_by_player[pid] = cards_played

    for move in moves:
        description = move.get('description', '')
        # Check if the move is by the correct player and involves adding an animal to Predators
        if player_name in description and "adds Animal to Predators" in description:
            # Extract the source of the animal
            parts = description.split('|')
            if len(parts) > 0:
                source_part = parts[0]
                for source, vp in STOLEN_ANIMAL_VP.items():
                    if source in source_part:
                        # Determine if the stolen card was played by self or opponent
                        stolen_from_self = False
                        stolen_from_opponent = False
                        
                        # Check if current player has this card type
                        if source in cards_played_by_player.get(player_id, []):
                            stolen_from_self = True
                        
                        # Check if any opponent has this card type
                        for pid, cards in cards_played_by_player.items():
                            if pid != player_id and source in cards:
                                stolen_from_opponent = True
                                break
                        
                        # If both players have the card, we need to make a decision
                        # In this case, we'll assume it's stolen from opponent (more common scenario)
                        if stolen_from_self and stolen_from_opponent:
                            stolen_vp_from_opponent += vp
                        elif stolen_from_self and not stolen_from_opponent:
                            stolen_vp_from_self += vp
                        elif stolen_from_opponent and not stolen_from_self:
                            stolen_vp_from_opponent += vp
                        # If neither player has the card in cards_played, default to opponent
                        else:
                            stolen_vp_from_opponent += vp
                        break
    
    return stolen_vp_from_opponent, stolen_vp_from_self

def process_game_for_animal_vp(file_path):
    """
    Process a single game file to extract animal card VP data for all players.
    Returns list of animal card VP data or empty list if processing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)

        # Check player count
        if len(game_data.get('players', [])) > 2:
            return []
        
        # Check if final_state exists and get final generation
        final_move = game_data["moves"][-1]
        final_state = final_move.get("game_state")
        if not final_state:
            print(f"Warning: No final_state found in {file_path}")
            return []
        final_generation = final_state.get('generation')
        if final_generation is None:
            print(f"Warning: No final_generation found in {file_path}")
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

            # Get player and opponent Elo
            elo_data = player_info.get('elo_data')
            player_elo = elo_data.get('game_rank') if elo_data else None
            opponent_elo = None
            if len(players) == 2:
                opponent_id = next((pid for pid in players if pid != player_id), None)
                if opponent_id:
                    opponent_info = players.get(opponent_id, {})
                    opponent_elo_data = opponent_info.get('elo_data')
                    opponent_elo = opponent_elo_data.get('game_rank') if opponent_elo_data else None
            
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
                        stolen_vp = 0

                        # If the card is Predators, calculate stolen VP
                        stolen_vp_from_opponent = 0
                        stolen_vp_from_self = 0
                        if animal_card == "Predators":
                            stolen_vp_from_opponent, stolen_vp_from_self = calculate_predators_stolen_vp(
                                game_data.get('moves', []), player_id, game_data)
                        
                        plants_denied_opponent = 0
                        plants_denied_self = 0
                        if animal_card in PLANT_REDUCTION_CARDS:
                            # Find the move index where the card was played to check the next move
                            for i, move in enumerate(game_data.get('moves', [])):
                                if move.get('player_id') == player_id and move.get('card_played') == animal_card:
                                    plants_denied_opponent, plants_denied_self = calculate_plants_denied(
                                        game_data.get('moves', []), i, player_id, animal_card, PLANT_REDUCTION_CARDS[animal_card], final_generation
                                    )
                                    break

                        # Add to results (include even if VP is 0, since card was played)
                        animal_vp_data.append({
                            'card_name': animal_card,
                            'vp': vp_value,
                            'stolen_vp_from_opponent': stolen_vp_from_opponent,
                            'stolen_vp_from_self': stolen_vp_from_self,
                            'plants_denied_opponent': plants_denied_opponent,
                            'plants_denied_self': plants_denied_self,
                            'player_id': player_id,
                            'player_name': player_name,
                            'corporation': corporation,
                            'player_elo': player_elo,
                            'opponent_elo': opponent_elo,
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
        'total_stolen_vp_from_opponent': 0,
        'total_stolen_vp_from_self': 0,
        'total_plants_denied_opponent': 0,
        'total_plants_denied_self': 0,
        'times_played': 0,
        'vp_values': [],
        'stolen_vp_from_opponent_values': [],
        'stolen_vp_from_self_values': [],
        'plants_denied_opponent_values': [],
        'plants_denied_self_values': [],
        'instances': []
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
                stolen_vp_from_opponent = animal_data.get('stolen_vp_from_opponent', 0)
                stolen_vp_from_self = animal_data.get('stolen_vp_from_self', 0)
                plants_denied_opponent = animal_data.get('plants_denied_opponent', 0)
                plants_denied_self = animal_data.get('plants_denied_self', 0)
                
                # Update card statistics
                card_stats[card_name]['total_vp'] += vp_value
                card_stats[card_name]['times_played'] += 1
                card_stats[card_name]['vp_values'].append(vp_value)
                card_stats[card_name]['instances'].append(animal_data)

                if stolen_vp_from_opponent > 0:
                    card_stats[card_name]['total_stolen_vp_from_opponent'] += stolen_vp_from_opponent
                    card_stats[card_name]['stolen_vp_from_opponent_values'].append(stolen_vp_from_opponent)

                if stolen_vp_from_self > 0:
                    card_stats[card_name]['total_stolen_vp_from_self'] += stolen_vp_from_self
                    card_stats[card_name]['stolen_vp_from_self_values'].append(stolen_vp_from_self)
                
                if plants_denied_opponent > 0:
                    card_stats[card_name]['total_plants_denied_opponent'] += plants_denied_opponent
                    card_stats[card_name]['plants_denied_opponent_values'].append(plants_denied_opponent)

                if plants_denied_self > 0:
                    card_stats[card_name]['total_plants_denied_self'] += plants_denied_self
                    card_stats[card_name]['plants_denied_self_values'].append(plants_denied_self)
                
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
            avg_stolen_vp_from_opponent = stats['total_stolen_vp_from_opponent'] / stats['times_played'] if stats['times_played'] > 0 else 0
            avg_stolen_vp_from_self = stats['total_stolen_vp_from_self'] / stats['times_played'] if stats['times_played'] > 0 else 0
            avg_plants_denied_opponent = stats['total_plants_denied_opponent'] / stats['times_played'] if stats['times_played'] > 0 else 0
            avg_plants_denied_self = stats['total_plants_denied_self'] / stats['times_played'] if stats['times_played'] > 0 else 0
            
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
                'avg_stolen_vp_from_opponent': avg_stolen_vp_from_opponent,
                'avg_stolen_vp_from_self': avg_stolen_vp_from_self,
                'avg_plants_denied_opponent': avg_plants_denied_opponent,
                'avg_plants_denied_self': avg_plants_denied_self,
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
    
    print(f"\n{'Rank':<4} {'Card Name':<18} {'Times Played':<12} {'Avg VP':<8} {'Avg Stolen VP':<15} {'Avg Plants Denied Opponent':<28} {'Avg Plants Denied Self':<25} {'Total VP':<9} {'Min':<4} {'Max':<4} {'Std Dev':<8}")
    print("-" * 180)
    
    for rank, (card_name, stats) in enumerate(sorted_cards, 1):
        if card_name == "Predators":
            total_stolen = stats.get('avg_stolen_vp_from_opponent', 0) + stats.get('avg_stolen_vp_from_self', 0)
            avg_stolen_vp_str = f"{total_stolen:.2f}"
        else:
            avg_stolen_vp_str = "-"
        avg_plants_denied_opponent_str = f"{stats.get('avg_plants_denied_opponent', 0):.2f}" if card_name in PLANT_REDUCTION_CARDS else "-"
        avg_plants_denied_self_str = f"{stats.get('avg_plants_denied_self', 0):.2f}" if card_name in PLANT_REDUCTION_CARDS else "-"
        print(f"{rank:<4} {card_name:<18} {stats['times_played']:<12} "
              f"{stats['avg_vp']:<8.2f} {avg_stolen_vp_str:<15} {avg_plants_denied_opponent_str:<28} {avg_plants_denied_self_str:<25} {stats['total_vp']:<9} "
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
        fieldnames = ['card_name', 'vp', 'stolen_vp_from_opponent', 'stolen_vp_from_self', 'plants_denied_opponent', 'plants_denied_self',
                     'player_id', 'player_name', 'corporation', 'player_elo', 'opponent_elo', 
                     'replay_id', 'game_date']
        
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
                     'avg_stolen_vp_from_opponent', 'avg_stolen_vp_from_self', 'avg_plants_denied_opponent', 'avg_plants_denied_self', 
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
                    'avg_stolen_vp_from_opponent': round(stats.get('avg_stolen_vp_from_opponent', 0), 4),
                    'avg_stolen_vp_from_self': round(stats.get('avg_stolen_vp_from_self', 0), 4),
                    'avg_plants_denied_opponent': round(stats.get('avg_plants_denied_opponent', 0), 4),
                    'avg_plants_denied_self': round(stats.get('avg_plants_denied_self', 0), 4),
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
    detailed_output_file = script_dir / "data" / "animal_cards_vp_detailed.csv"
    summary_output_file = script_dir / "data" / "animal_cards_vp_summary.csv"
    
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
