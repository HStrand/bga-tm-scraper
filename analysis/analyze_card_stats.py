#!/usr/bin/env python3
"""
Analyze win rates, ELO gain, and ELO rating per card in Terraforming Mars games.

This script processes all parsed game files to calculate statistics for each card played.
The statistics include win rate, average ELO gain, and average ELO of the player who played the card.

The winner is determined using the 'winner' field from the game data.
When a player plays multiple cards in a single game, each card is counted as a separate data point.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
import csv

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

def normalize_corporation_name(raw_name):
    """
    Normalize corporation names to their full official names.
    Maps abbreviated or truncated names to their complete versions.
    """
    if not raw_name:
        return "Unknown"
    
    name_mapping = {
        "Valley": "Valley Trust",
        "Mining": "Mining Guild",
        "Point": "Point Luna", 
        "Robinson": "Robinson Industries",
        "Cheung": "Cheung Shing Mars",
        "Interplanetary": "Interplanetary Cinematics",
        "Tharsis": "Tharsis Republic",
        "Saturn": "Saturn Systems",
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
    
    return name_mapping.get(raw_name, raw_name)

def extract_cards_from_player(player_data):
    """
    Extract cards from a player's cards_played array.
    """
    return player_data.get('cards_played', [])

def determine_game_winner(game_data, players):
    """
    Determine the winner using the 'winner' field from game data.
    Returns the player_id of the winner by matching player_name.
    """
    winner_name = game_data.get('winner')
    if not winner_name:
        return None
    
    for player_id, player_data in players.items():
        if player_data.get('player_name') == winner_name:
            return player_id
    
    return None

def process_game_for_card_data(file_path, prelude_set):
    """
    Process a single game file to extract card data and determine winner.
    Returns list of card data dictionaries or empty list if processing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)

        if game_data.get('colonies_on'):
            return []

        players = game_data.get('players', {})
        if len(players) != 2:
            return []
        
        if not players:
            print(f"Warning: No players found in {file_path}")
            return []
        
        winner_id = determine_game_winner(game_data, players)
        if not winner_id:
            print(f"Warning: Could not determine winner in {file_path}")
            return []
        
        card_data_list = []
        
        for player_id, player_data in players.items():
            cards = extract_cards_from_player(player_data)
            
            if not cards:
                continue
            
            # Get opponent Elo
            opponent_id = next((pid for pid in players if pid != player_id), None)
            opponent_elo = None
            if opponent_id:
                opponent_info = players.get(opponent_id, {})
                opponent_elo_data = opponent_info.get('elo_data')
                if opponent_elo_data:
                    opponent_elo = opponent_elo_data.get('game_rank')

            for card in cards:
                if card in prelude_set:
                    continue

                elo_data = player_data.get('elo_data')
                elo_change = None
                elo_rating = None
                if elo_data and isinstance(elo_data, dict):
                    elo_change = elo_data.get('game_rank_change')
                    elo_rating = elo_data.get('game_rank')
                
                card_data = {
                    'card': card,
                    'player_id': player_id,
                    'player_name': player_data.get('player_name', 'Unknown'),
                    'corporation': normalize_corporation_name(player_data.get('corporation', 'Unknown')),
                    'final_vp': player_data.get('final_vp', 0),
                    'won_game': player_id == winner_id,
                    'elo_change': elo_change,
                    'elo_rating': elo_rating,
                    'opponent_elo': opponent_elo,
                    'replay_id': game_data.get('replay_id', 'unknown'),
                    'game_date': game_data.get('game_date', 'unknown')
                }
                card_data_list.append(card_data)
        
        return card_data_list
        
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
    
    for player_dir in data_path.iterdir():
        if player_dir.is_dir() and player_dir.name.isdigit():
            for game_file in player_dir.glob("*.json"):
                game_files.append(game_file)
    
    return game_files

def analyze_card_stats(data_dir, prelude_set):
    """
    Main analysis function that processes all games and calculates card statistics.
    """
    print("Starting Card Stats analysis...")
    
    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")
    
    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, []
    
    card_stats = defaultdict(lambda: {
        'total_played': 0,
        'total_wins': 0,
        'total_elo_change': 0,
        'total_elo_rating': 0,
        'elo_changes': [],
        'elo_ratings': [],
        'play_instances': []
    })
    
    all_card_data = []
    total_games_processed = 0
    total_card_instances = 0
    
    for i, game_file in enumerate(game_files):
        card_data_list = process_game_for_card_data(game_file, prelude_set)
        
        if card_data_list:
            total_games_processed += 1
            
            for card_data in card_data_list:
                card = card_data['card']
                won_game = card_data['won_game']
                elo_change = card_data['elo_change']
                elo_rating = card_data['elo_rating']
                
                card_stats[card]['total_played'] += 1
                if won_game:
                    card_stats[card]['total_wins'] += 1
                
                if elo_change is not None:
                    card_stats[card]['total_elo_change'] += elo_change
                    card_stats[card]['elo_changes'].append(elo_change)
                
                if elo_rating is not None:
                    card_stats[card]['total_elo_rating'] += elo_rating
                    card_stats[card]['elo_ratings'].append(elo_rating)
                
                card_stats[card]['play_instances'].append(card_data)
                
                all_card_data.append(card_data)
                total_card_instances += 1
        
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} games...")
    
    print(f"\nAnalysis complete!")
    print(f"Games processed: {total_games_processed}")
    print(f"Total card instances: {total_card_instances}")
    print(f"Unique cards: {len(card_stats)}")
    
    card_results = {}
    for card, stats in card_stats.items():
        win_rate = stats['total_wins'] / stats['total_played'] if stats['total_played'] > 0 else 0
        
        elo_changes = stats['elo_changes']
        elo_ratings = stats['elo_ratings']
        avg_elo_change = stats['total_elo_change'] / len(elo_changes) if elo_changes else 0
        avg_elo_rating = stats['total_elo_rating'] / len(elo_ratings) if elo_ratings else 0
        min_elo_change = min(elo_changes) if elo_changes else 0
        max_elo_change = max(elo_changes) if elo_changes else 0
        
        card_results[card] = {
            'card': card,
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
    
    return card_results, all_card_data

def display_results(card_results):
    """Display analysis results."""
    if not card_results:
        print("No results to display.")
        return
    
    print("\n" + "="*110)
    print("CARD WIN RATES AND ELO ANALYSIS RESULTS")
    print("="*110)
    
    sorted_cards = sorted(card_results.items(), 
                            key=lambda x: x[1]['avg_elo_change'], 
                            reverse=True)
    
    print(f"\n{'Rank':<4} {'Card':<35} {'Played':<7} {'Win Rate':<9} {'Avg ELO Δ':<9} {'Avg ELO':<8}")
    print("-" * 100)
    
    for rank, (card, stats) in enumerate(sorted_cards, 1):
        print(f"{rank:<4} {card:<35} {stats['total_played']:<7} "
              f"{stats['win_rate']*100:<9.1f}% "
              f"{stats['avg_elo_change']:<9.2f} {stats['avg_elo_rating']:<8.0f}")

def save_detailed_results_to_csv(all_card_data, output_file):
    """Save detailed game-by-game card results to a CSV file."""
    if not all_card_data:
        print("No detailed results to save.")
        return
    
    try:
        fieldnames = ['card', 'player_id', 'player_name', 'corporation', 
                     'final_vp', 'won_game', 'elo_change', 'elo_rating', 'opponent_elo', 'replay_id', 'game_date']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            sorted_results = sorted(all_card_data, 
                                  key=lambda x: (x['card'], x['game_date']))
            
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
        fieldnames = ['card', 'total_played', 'win_rate', 
                     'avg_elo_change', 'avg_elo_rating']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            sorted_cards = sorted(card_results.items(), 
                                   key=lambda x: x[1]['avg_elo_change'], 
                                   reverse=True)
            
            for card, stats in sorted_cards:
                row = {
                    'card': card,
                    'total_played': stats['total_played'],
                    'win_rate': round(stats['win_rate'], 4),
                    'avg_elo_change': round(stats['avg_elo_change'], 4),
                    'avg_elo_rating': round(stats['avg_elo_rating'], 1)
                }
                writer.writerow(row)
        
        print(f"\nCard summary saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving card summary CSV file: {e}")

def main():
    """Main function to run the Card Stats analysis."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    output_dir = script_dir
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    detailed_output_file = output_dir / "card_stats_detailed.csv"
    summary_output_file = output_dir / "card_stats_summary.csv"
    
    print("Terraforming Mars - Card Stats Analysis")
    print("=" * 50)
    
    prelude_set = load_prelude_list()
    if not prelude_set:
        print("Warning: Could not load prelude list. Continuing without filtering prelude cards.")

    card_results, all_card_data = analyze_card_stats(data_dir, prelude_set)
    
    if card_results:
        display_results(card_results)
        
        save_detailed_results_to_csv(all_card_data, detailed_output_file)
        save_card_summary_to_csv(card_results, summary_output_file)
        
        print(f"\nAnalysis complete! Check the CSV files in {output_dir} for detailed data.")
    else:
        print("No data found to analyze.")

if __name__ == "__main__":
    main()
