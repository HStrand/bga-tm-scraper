#!/usr/bin/env python3
"""
Analyze the most valuable city locations on the Tharsis map from Terraforming Mars games.

This script processes all parsed game files to determine the full economic value of cities:
- Immediate tile bonuses when placing cities (resources from tiles.json)
- Ocean adjacency bonuses when placing cities (2 M€ per adjacent ocean)
- Ongoing bonuses when placing greeneries adjacent to cities (including ocean adjacencies)
- Total resources gained per city location across all games
- Average resources per city placement by location

Only bonuses gained by the player who owns each city are counted.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
import csv

def load_tiles_data(tiles_file):
    """Load and index the tiles data from tiles.json."""
    try:
        with open(tiles_file, 'r', encoding='utf-8') as f:
            tiles_data = json.load(f)
        
        # Create a lookup dictionary by tile name
        tiles_lookup = {}
        for tile in tiles_data['tiles']:
            tiles_lookup[tile['name']] = tile
        
        return tiles_lookup
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error loading tiles data: {e}")
        return {}

def normalize_tile_location(raw_location):
    """Convert 'Tharsis Hex 6,4 (6,4)' to 'Tharsis Hex 6,4'."""
    if raw_location and '(' in raw_location:
        return raw_location.split(' (')[0]
    return raw_location

def get_tile_resources(tile_name, tiles_lookup):
    """Get resources from a tile, returns dict of resource_type: count."""
    if tile_name not in tiles_lookup:
        return {}
    
    resources = {}
    for resource in tiles_lookup[tile_name].get('resources', []):
        resource_type = resource['type']
        resource_count = resource['count']
        resources[resource_type] = resources.get(resource_type, 0) + resource_count
    
    return resources

def count_ocean_adjacencies(tile_name, ocean_state, tiles_lookup):
    """Count how many adjacent tiles have oceans."""
    if tile_name not in tiles_lookup:
        return 0
    
    ocean_count = 0
    adjacencies = tiles_lookup[tile_name].get('adjacencies', [])
    
    for adjacent_tile in adjacencies:
        if ocean_state.get(adjacent_tile, False):
            ocean_count += 1
    
    return ocean_count

def get_adjacent_cities(tile_name, city_owners, tiles_lookup):
    """Get list of (city_location, owner_player_id) for cities adjacent to this tile."""
    if tile_name not in tiles_lookup:
        return []
    
    adjacent_cities = []
    adjacencies = tiles_lookup[tile_name].get('adjacencies', [])
    
    for adjacent_tile in adjacencies:
        if adjacent_tile in city_owners:
            adjacent_cities.append((adjacent_tile, city_owners[adjacent_tile]))
    
    return adjacent_cities

def process_game_for_city_values(file_path, tiles_lookup):
    """
    Process a single game file to calculate full city values.
    Returns dict of city_location -> {player_id, resources_gained, generation_placed}
    """
    city_values = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        
        if 'moves' not in game_data:
            return city_values
        
        moves = game_data['moves']
        
        # Track game state
        ocean_state = {}  # tile_name -> True if has ocean
        city_owners = {}  # tile_name -> player_id who owns the city
        
        # Process moves chronologically
        for move in moves:
            if 'tile_placed' not in move or 'tile_location' not in move:
                continue
            
            tile_type = move['tile_placed']
            raw_location = move['tile_location']
            normalized_location = normalize_tile_location(raw_location)
            player_id = move.get('player_id')
            
            # Get current generation from game state
            current_generation = None
            if 'game_state' in move and 'generation' in move['game_state']:
                current_generation = move['game_state']['generation']
            
            if not normalized_location or not player_id:
                continue
            
            # Skip space cities that don't have tile adjacencies
            if normalized_location in ['Ganymede Colony', 'Phobos Space Haven']:
                continue
            
            # Track ocean placements
            if tile_type == 'Ocean':
                ocean_state[normalized_location] = True
            
            # Process city placements
            elif tile_type == 'City':
                city_owners[normalized_location] = player_id
                
                # Initialize city value tracking
                if normalized_location not in city_values:
                    city_values[normalized_location] = {
                        'player_id': player_id,
                        'resources': defaultdict(int),
                        'generation_placed': current_generation
                    }
                
                # Add immediate tile bonuses
                tile_resources = get_tile_resources(normalized_location, tiles_lookup)
                for resource_type, count in tile_resources.items():
                    city_values[normalized_location]['resources'][resource_type] += count
                
                # Add ocean adjacency bonuses (2 M€ per adjacent ocean)
                ocean_adjacencies = count_ocean_adjacencies(normalized_location, ocean_state, tiles_lookup)
                if ocean_adjacencies > 0:
                    city_values[normalized_location]['resources']['M€'] += ocean_adjacencies * 2
            
            # Process greenery placements (Forest)
            elif tile_type == 'Forest':
                # Get tile resources for the greenery
                greenery_resources = get_tile_resources(normalized_location, tiles_lookup)
                
                # Count ocean adjacencies for the greenery tile
                greenery_ocean_adjacencies = count_ocean_adjacencies(normalized_location, ocean_state, tiles_lookup)
                
                # Find adjacent cities and award bonuses to their owners
                adjacent_cities = get_adjacent_cities(normalized_location, city_owners, tiles_lookup)
                
                for city_location, city_owner in adjacent_cities:
                    if city_location in city_values and city_values[city_location]['player_id'] == city_owner:
                        # Award tile resources to city owner
                        for resource_type, count in greenery_resources.items():
                            city_values[city_location]['resources'][resource_type] += count
                        
                        # Award ocean adjacency bonuses to city owner
                        if greenery_ocean_adjacencies > 0:
                            city_values[city_location]['resources']['M€'] += greenery_ocean_adjacencies * 2
        
        # Add VP from final state
        final_state = game_data['moves'][-1]
        for player_id, player_data in final_state['game_state']['player_vp'].items():
            if 'details' in player_data and 'cities' in player_data['details']:
                cities = player_data['details']['cities']
                for city_location, city_info in cities.items():
                    # Skip space cities
                    if city_location in ['Ganymede Colony', 'Phobos Space Haven']:
                        continue
                    if city_location in city_values and 'vp' in city_info:
                        city_values[city_location]['resources']['VP'] += city_info['vp']
            
        
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print(f"Warning: Could not process {file_path}: {e}")
    
    return city_values

def find_all_game_files(data_dir):
    """Find all JSON game files in the parsed data directory."""
    game_files = []
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"Error: Data directory {data_dir} does not exist")
        return game_files
    
    # Look for all JSON files in player subdirectories
    for player_dir in data_path.iterdir():
        if player_dir.is_dir():
            for game_file in player_dir.glob("*.json"):
                game_files.append(game_file)
    
    return game_files

def analyze_city_locations(data_dir, tiles_lookup):
    """
    Main analysis function that processes all games and calculates city location statistics.
    """
    print("Starting city location analysis...")
    
    # Find all game files
    game_files = find_all_game_files(data_dir)
    print(f"Found {len(game_files)} game files to process")
    
    if not game_files:
        print("No game files found. Please check the data directory.")
        return None, 0, 0
    
    # Data structures for aggregation
    location_stats = defaultdict(lambda: {
        'placement_count': 0,
        'total_resources': defaultdict(int),
        'resource_lists': defaultdict(list),  # For calculating averages
        'generation_values': []  # For tracking generation placements
    })
    
    processed_games = 0
    total_cities = 0
    
    # Process each game file
    for i, game_file in enumerate(game_files):
        city_values = process_game_for_city_values(game_file, tiles_lookup)
        
        if city_values:
            processed_games += 1
            total_cities += len(city_values)
            
            # Aggregate data by location
            for city_location, city_data in city_values.items():
                location_stats[city_location]['placement_count'] += 1
                
                # Aggregate resources
                for resource_type, count in city_data['resources'].items():
                    location_stats[city_location]['total_resources'][resource_type] += count
                    location_stats[city_location]['resource_lists'][resource_type].append(count)
                
                # Track generation placement
                if city_data.get('generation_placed') is not None:
                    location_stats[city_location]['generation_values'].append(city_data['generation_placed'])
        
        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1} games...")
    
    print(f"\nAnalysis complete!")
    print(f"Processed {processed_games} games with city data")
    print(f"Total cities analyzed: {total_cities}")
    print(f"Unique city locations: {len(location_stats)}")
    
    # Calculate averages and prepare results
    results = []
    resource_types = set()
    
    for location, stats in location_stats.items():
        result = {
            'location': location,
            'placement_count': stats['placement_count'],
            'frequency_percent': round((stats['placement_count'] / processed_games) * 100, 2)
        }
        
        # Add total and average for each resource type
        for resource_type, total_count in stats['total_resources'].items():
            resource_types.add(resource_type)
            result[f'total_{resource_type}'] = total_count
            result[f'avg_{resource_type}'] = round(total_count / stats['placement_count'], 2)
        
        # Calculate total economic value with proper resource values
        # M€ = 1, Steel = 2, Titanium = 3, Plant = 2, Card = 3
        resource_values = {'M€': 1, 'Steel': 2, 'Titanium': 3, 'Plant': 2, 'Card': 3}
        total_economic_value = 0
        for resource_type, multiplier in resource_values.items():
            total_economic_value += stats['total_resources'].get(resource_type, 0) * multiplier
        
        result['total_economic_value'] = total_economic_value
        result['avg_economic_value'] = round(total_economic_value / stats['placement_count'], 2)
        
        # Calculate average generation
        if stats['generation_values']:
            avg_generation = round(sum(stats['generation_values']) / len(stats['generation_values']), 1)
            result['avg_generation'] = avg_generation
        else:
            result['avg_generation'] = None
        
        results.append(result)
    
    return results, processed_games, total_cities, sorted(resource_types)

def display_results(results, resource_types):
    """Display analysis results."""
    if not results:
        print("No results to display.")
        return
    
    print("\n" + "="*100)
    print("CITY LOCATION ANALYSIS RESULTS")
    print("="*100)
    
    # Sort by total economic value
    print(f"\nTOP 15 LOCATIONS BY TOTAL ECONOMIC VALUE:")
    print("-" * 130)
    header = f"{'Location':<25} {'Count':<6} {'Freq%':<6} {'Econ Val':<8} {'Avg Econ':<8} {'Avg Gen':<8} {'VP':<6} {'M€':<6} {'Steel':<6} {'Titan':<6} {'Plant':<6} {'Card':<6}"
    print(header)
    print("-" * 130)
    
    sorted_by_economic = sorted(results, key=lambda x: x.get('total_economic_value', 0), reverse=True)
    for result in sorted_by_economic[:15]:
        avg_gen_str = str(result['avg_generation']) if result['avg_generation'] is not None else "N/A"
        row = f"{result['location']:<25} {result['placement_count']:<6} {result['frequency_percent']:<6} "
        row += f"{result.get('total_economic_value', 0):<8} {result.get('avg_economic_value', 0):<8} {avg_gen_str:<8} "
        row += f"{result.get('total_VP', 0):<6} {result.get('total_M€', 0):<6} "
        row += f"{result.get('total_Steel', 0):<6} {result.get('total_Titanium', 0):<6} "
        row += f"{result.get('total_Plant', 0):<6} {result.get('total_Card', 0):<6}"
        print(row)
    
    # Sort by average economic value (min 3 placements)
    print(f"\nTOP 15 LOCATIONS BY AVERAGE ECONOMIC VALUE (min 3 placements):")
    print("-" * 130)
    print(header)
    print("-" * 130)
    
    filtered_results = [r for r in results if r['placement_count'] >= 3]
    sorted_by_avg_economic = sorted(filtered_results, key=lambda x: x.get('avg_economic_value', 0), reverse=True)
    for result in sorted_by_avg_economic[:15]:
        avg_gen_str = str(result['avg_generation']) if result['avg_generation'] is not None else "N/A"
        row = f"{result['location']:<25} {result['placement_count']:<6} {result['frequency_percent']:<6} "
        row += f"{result.get('total_economic_value', 0):<8} {result.get('avg_economic_value', 0):<8} {avg_gen_str:<8} "
        row += f"{result.get('total_VP', 0):<6} {result.get('total_M€', 0):<6} "
        row += f"{result.get('total_Steel', 0):<6} {result.get('total_Titanium', 0):<6} "
        row += f"{result.get('total_Plant', 0):<6} {result.get('total_Card', 0):<6}"
        print(row)
    
    # Sort by total VP
    print(f"\nTOP 15 LOCATIONS BY TOTAL VP:")
    print("-" * 130)
    print(header)
    print("-" * 130)
    
    sorted_by_vp = sorted(results, key=lambda x: x.get('total_VP', 0), reverse=True)
    for result in sorted_by_vp[:15]:
        avg_gen_str = str(result['avg_generation']) if result['avg_generation'] is not None else "N/A"
        row = f"{result['location']:<25} {result['placement_count']:<6} {result['frequency_percent']:<6} "
        row += f"{result.get('total_economic_value', 0):<8} {result.get('avg_economic_value', 0):<8} {avg_gen_str:<8} "
        row += f"{result.get('total_VP', 0):<6} {result.get('total_M€', 0):<6} "
        row += f"{result.get('total_Steel', 0):<6} {result.get('total_Titanium', 0):<6} "
        row += f"{result.get('total_Plant', 0):<6} {result.get('total_Card', 0):<6}"
        print(row)

def save_results_to_csv(results, resource_types, output_file):
    """Save detailed results to a CSV file."""
    try:
        # Build fieldnames dynamically based on available resource types
        base_fields = ['location', 'placement_count', 'frequency_percent', 'total_economic_value', 'avg_economic_value', 'avg_generation']
        
        resource_fields = []
        for resource_type in sorted(resource_types):
            resource_fields.extend([f'total_{resource_type}', f'avg_{resource_type}'])
        
        fieldnames = base_fields + resource_fields
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            # Sort by total economic value for CSV output
            sorted_results = sorted(results, key=lambda x: x.get('total_economic_value', 0), reverse=True)
            for result in sorted_results:
                # Ensure all fields exist in the result
                csv_row = {}
                for field in fieldnames:
                    csv_row[field] = result.get(field, 0)
                writer.writerow(csv_row)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving CSV file: {e}")

def main():
    """Main function to run the city location analysis."""
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data" / "parsed"
    tiles_file = script_dir / "tiles.json"
    output_file = script_dir / "city_locations_analysis.csv"
    
    print("Terraforming Mars - City Location Analysis")
    print("=" * 50)
    
    # Load tiles data
    print("Loading tiles data...")
    tiles_lookup = load_tiles_data(tiles_file)
    if not tiles_lookup:
        print("Failed to load tiles data. Exiting.")
        return
    
    print(f"Loaded data for {len(tiles_lookup)} tiles")
    
    # Run the analysis
    results, processed_games, total_cities, resource_types = analyze_city_locations(data_dir, tiles_lookup)
    
    if results:
        # Display results
        display_results(results, resource_types)
        
        # Save to CSV
        save_results_to_csv(results, resource_types, output_file)
        
        print(f"\n" + "="*100)
        print("SUMMARY STATISTICS:")
        print(f"Games processed: {processed_games}")
        print(f"Total cities analyzed: {total_cities}")
        print(f"Unique city locations: {len(results)}")
        print(f"Average cities per game: {round(total_cities / processed_games, 1)}")
        print(f"Resource types tracked: {', '.join(sorted(resource_types))}")
        print("="*100)
    else:
        print("No data found to analyze.")

if __name__ == "__main__":
    main()
