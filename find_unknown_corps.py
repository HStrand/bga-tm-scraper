import os
import json
import re
import csv

def find_games_with_unknown_corporations():
    """
    Scans all JSON files in the parsed data directory to find games where a player's corporation is "Unknown".
    """
    parsed_data_dir = 'data/parsed'
    report_file = 'unknown_corporations_report.csv'
    games_with_unknown_corps = []

    if not os.path.exists(parsed_data_dir):
        print(f"Parsed data directory not found: {parsed_data_dir}")
        return

    print("Scanning all JSON files in parsed/ for games with 'Unknown' corporations...")

    for root, _, files in os.walk(parsed_data_dir):
        for file in files:
            if file.endswith('.json'):
                json_path = os.path.join(root, file)
                
                # Extract table_id and player_id from filename or path
                table_id_match = re.search(r'game_(\d+)', file)
                table_id = table_id_match.group(1) if table_id_match else 'Unknown'
                
                player_id_perspective = os.path.basename(root)

                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        game_data = json.load(f)
                    
                    if 'players' in game_data and isinstance(game_data['players'], dict):
                        for p_id, player_data in game_data['players'].items():
                            if isinstance(player_data, dict) and player_data.get('corporation') == 'Unknown':
                                games_with_unknown_corps.append({
                                    'table_id': table_id,
                                    'player_id_perspective': player_id_perspective,
                                    'player_name_with_unknown_corp': player_data.get('player_name', 'N/A'),
                                    'file_path': json_path
                                })
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON for {json_path}")
                except Exception as e:
                    print(f"An error occurred while processing {json_path}: {e}")

    if games_with_unknown_corps:
        print(f"\nFound {len(games_with_unknown_corps)} games with 'Unknown' corporations.")
        
        # Write to CSV
        with open(report_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['table_id', 'player_id_perspective', 'player_name_with_unknown_corp', 'file_path'])
            writer.writeheader()
            writer.writerows(games_with_unknown_corps)
        
        print(f"Report saved to {report_file}")
    else:
        print("\nNo games with 'Unknown' corporations found.")

if __name__ == '__main__':
    find_games_with_unknown_corporations()
