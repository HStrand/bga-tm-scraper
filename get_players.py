from datetime import datetime
import json
import config
from bga_tm_scraper.bga_session import BGASession

BASE_URL = 'https://boardgamearena.com'
RANKING_URL = '/gamepanel/gamepanel/getRanking.html'

session = BGASession(
        email=config.BGA_EMAIL,
        password=config.BGA_PASSWORD,
        chromedriver_path=config.CHROMEDRIVER_PATH,
        chrome_path=config.CHROME_PATH,
        headless=True
    )

print("Logging into BGA")
session.login()

params = {'game': 1924}

num_players = 100000
players = []

print("Fetching up to", num_players, "players")

for start in range(0, num_players, 10):
    params['start'] = start
    resp = session.get(f'{BASE_URL}{RANKING_URL}', params=params)
    
    data = resp.json()
    
    if 'data' not in data or 'ranks' not in data['data']:
        print(f"Unexpected response format at start={start}")
        break
        
    ranks_data = data['data']['ranks']
    if not ranks_data:
        print(f"No more players found at start={start}")
        break
            
    for player in ranks_data:
        if len(players) >= num_players:
            break

        try:
            player_id = int(player['id'])
            player_name = player['name']
            country = player['country']['name'] if player.get('country') else 'Unknown'
            elo = int(round(float(player['ranking']))) - 1300
            updated_at = str(datetime.utcnow())
            players.append(
                {
                    'playerId': player_id, 
                    'name': player_name, 
                    'country': country,
                    'elo': elo, 
                    'updatedAt': updated_at
                })

        except (KeyError, ValueError, TypeError) as e:
            print(f"Error parsing player data: {e}, player: {player}")
            continue

    # If we got fewer than 10 players, we've reached the end
    if len(ranks_data) < 10:
        break
        
    print("Fetched", len(players), "players")

with open("data/registry/players.json", "w") as f:
    json.dump(players, f)