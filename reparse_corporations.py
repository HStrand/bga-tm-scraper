import os
import json
import re
import csv

def reparse_corporations_from_moves():
    """
    Scans games with "Unknown" corporations and attempts to fix them by parsing move descriptions.
    """
    report_file = 'unknown_corporations_report.csv'
    reparsed_dir = 'data/reparsed'
    
    if not os.path.exists(report_file):
        print(f"Report file not found: {report_file}")
        return

    os.makedirs(reparsed_dir, exist_ok=True)
    print(f"Created directory for reparsed files: {reparsed_dir}")

    with open(report_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        games_to_fix = list(reader)

    print(f"Found {len(games_to_fix)} games to reparse...")
    fixed_games_count = 0

    for game in games_to_fix:
        json_path = game['file_path']
        if not os.path.exists(json_path):
            print(f"Warning: JSON file not found: {json_path}")
            continue

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                game_data = json.load(f)

            if 'players' not in game_data or not isinstance(game_data['players'], dict):
                continue

            game_fixed = False
            for player_id, player_data in game_data['players'].items():
                if isinstance(player_data, dict) and player_data.get('corporation') == 'Unknown':
                    player_name = player_data.get('player_name')
                    if not player_name:
                        continue

                    corp_name = None
                    # Search for corporation in moves
                    for move in game_data.get('moves', []):
                        description = move.get('description', '')
                        
                        # Primary pattern
                        pattern = rf"{re.escape(player_name)}\s+chooses corporation\s+([A-Za-z\s]+)"
                        match = re.search(pattern, description)
                        if match:
                            corp_name = match.group(1).strip()
                            break

                        # Fallback pattern for player_perspective
                        if player_id == game_data.get('player_perspective'):
                            fallback_pattern = r"You choose corporation\s+([A-Za-z\s]+)"
                            fallback_match = re.search(fallback_pattern, description)
                            if fallback_match:
                                corp_name = fallback_match.group(1).strip()
                                break
                    
                    if corp_name:
                        # Handle potential trailing text
                        if '|' in corp_name:
                            corp_name = corp_name.split('|')[0].strip()
                        
                        player_data['corporation'] = corp_name
                        print(f"Fixed corporation for {player_name} in {os.path.basename(json_path)} -> {corp_name}")
                        game_fixed = True
            
            if game_fixed:
                fixed_games_count += 1
                # Save the updated file
                player_id_perspective = game['player_id_perspective']
                new_dir = os.path.join(reparsed_dir, player_id_perspective)
                os.makedirs(new_dir, exist_ok=True)
                
                new_path = os.path.join(new_dir, os.path.basename(json_path))
                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump(game_data, f, indent=4, ensure_ascii=False)

        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON for {json_path}")
        except Exception as e:
            print(f"An error occurred while processing {json_path}: {e}")

    print(f"\nReparsing complete. Fixed {fixed_games_count} out of {len(games_to_fix)} games.")

if __name__ == '__main__':
    reparse_corporations_from_moves()
