"""
Index Top Players Script
Fetches updated player list from BGA, updates via API, and indexes games for top 100 players by Elo
"""

import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import config
from bga_tm_scraper.bga_session import BGASession
from bga_tm_scraper.scraper import TMScraper
from bga_tm_scraper.parser import Parser
from gui.api_client import APIClient
from gui.version import BUILD_VERSION

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# BGA constants
BASE_URL = 'https://boardgamearena.com'
RANKING_URL = '/gamepanel/gamepanel/getRanking.html'


def fetch_players() -> List[Dict]:
    """
    Fetch all Terraforming Mars players from BGA leaderboard
    
    Returns:
        list: List of player dictionaries with id, name, country, elo, updatedAt
    """
    print("\n" + "="*80)
    print("STEP 1: Fetching players from BGA")
    print("="*80)
    
    session = BGASession(
        email=config.BGA_EMAIL,
        password=config.BGA_PASSWORD,
        chromedriver_path=config.CHROMEDRIVER_PATH,
        chrome_path=config.CHROME_PATH,
        headless=True
    )
    
    print("Logging into BGA...")
    if not session.login():
        raise RuntimeError("Failed to login to BGA")
    
    params = {'game': 1924}
    num_players = 1000 # Only top 1000
    players = []
    
    print(f"Fetching up to {num_players} players from leaderboard...")
    
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
                players.append({
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
            
        if len(players) % 100 == 0:
            print(f"Fetched {len(players)} players so far...")
    
    # Close the session
    session.close_browser()
    
    print(f"\n✅ Successfully fetched {len(players)} players")
    return players


def update_players_via_api(api_client: APIClient, players: List[Dict]) -> bool:
    """
    Update players via the API
    
    Args:
        api_client: APIClient instance
        players: List of player dictionaries
        
    Returns:
        bool: True if successful
    """
    print("\n" + "="*80)
    print("STEP 2: Updating players via API")
    print("="*80)
    
    print(f"Uploading {len(players)} players to API...")
    success = api_client.update_players(players)
    
    if success:
        print("✅ Successfully updated players via API")
    else:
        print("❌ Failed to update players via API")
    
    return success


def create_scraper_config() -> Dict:
    """
    Create scraper configuration from config.py
    
    Returns:
        dict: Configuration dictionary for scraper
    """
    return {
        'BGA_EMAIL': config.BGA_EMAIL,
        'BGA_PASSWORD': config.BGA_PASSWORD,
        'CHROME_PATH': config.CHROME_PATH,
        'CHROMEDRIVER_PATH': config.CHROMEDRIVER_PATH,
        'REQUEST_DELAY': config.REQUEST_DELAY,
        'CURRENT_SPEED': config.CURRENT_SPEED,
        'SPEED_PROFILE': config.SPEED_PROFILE
    }


def initialize_scraper() -> Tuple[TMScraper, Parser]:
    """
    Initialize scraper and parser
    
    Returns:
        tuple: (scraper, parser) instances
    """
    print("\n" + "="*80)
    print("Initializing scraper...")
    print("="*80)
    
    scraper = TMScraper(
        chromedriver_path=config.CHROMEDRIVER_PATH,
        chrome_path=config.CHROME_PATH,
        request_delay=config.REQUEST_DELAY,
        headless=True,
        email=config.BGA_EMAIL,
        password=config.BGA_PASSWORD
    )
    
    # Override speed settings
    scraper.speed_settings = config.CURRENT_SPEED
    scraper.speed_profile = config.SPEED_PROFILE
    
    parser = Parser()
    
    print("Starting browser and logging in...")
    if not scraper.start_browser_and_login():
        raise RuntimeError("Failed to start browser and login")
    
    print("✅ Scraper initialized successfully")
    return scraper, parser


def index_games_for_player(
    scraper: TMScraper,
    parser: Parser,
    api_client: APIClient,
    player_id: str,
    player_name: str
) -> Tuple[int, int]:
    """
    Index games for a single player
    
    Args:
        scraper: TMScraper instance
        parser: Parser instance
        api_client: APIClient instance
        player_id: Player ID to index
        player_name: Player name for display
        
    Returns:
        tuple: (successful_count, failed_count)
    """
    print(f"\n  🔍 Indexing games for {player_name} (ID: {player_id})...")
    
    try:
        # Get already indexed games from API
        indexed_games = api_client.get_indexed_games_by_player(player_id)
        print(f"  Found {len(indexed_games)} already indexed games")
        
        # Scrape player's game history
        print(f"  Scraping game history...")
        games_data = scraper.scrape_player_game_history(player_id, max_clicks=1000)
        
        if not games_data:
            print(f"  ⚠️ No games found for player {player_id}")
            return 0, 0
        
        print(f"  Found {len(games_data)} total games")
        
        # Filter out already indexed games
        new_games = [game for game in games_data if game['table_id'] not in indexed_games]
        print(f"  Processing {len(new_games)} new games (skipping {len(indexed_games)} already indexed)")
        
        successful = 0
        failed = 0
        
        # Process each new game
        for i, game_info in enumerate(new_games, 1):
            table_id = game_info['table_id']
            
            try:
                # Scrape table only (in memory)
                result = scraper.scrape_table_only(table_id, player_id, save_raw=False, raw_data_dir=None)
                
                if result and result.get('success'):
                    game_mode = result.get('game_mode', 'Normal mode')
                    
                    # Fallback to table date if game history date is invalid
                    if not game_info.get('parsed_datetime'):
                        table_date_info = result.get('game_date_info')
                        if table_date_info:
                            game_info['raw_datetime'] = table_date_info.get('raw_datetime', 'unknown')
                            game_info['parsed_datetime'] = table_date_info.get('parsed_datetime')
                    
                    elo_data = result.get('elo_data', {})
                    version = result.get('version')
                    
                    # Convert EloData objects to dictionaries
                    players_list = []
                    if elo_data:
                        for player_name_key, elo_obj in elo_data.items():
                            player_dict = {
                                'player_name': elo_obj.player_name or player_name_key,
                                'player_id': elo_obj.player_id,
                                'position': elo_obj.position,
                                'arena_points': elo_obj.arena_points,
                                'arena_points_change': elo_obj.arena_points_change,
                                'game_rank': elo_obj.game_rank,
                                'game_rank_change': elo_obj.game_rank_change
                            }
                            players_list.append(player_dict)
                    
                    # Create game data structure for API
                    game_api_data = {
                        'table_id': table_id,
                        'raw_datetime': game_info['raw_datetime'],
                        'parsed_datetime': game_info['parsed_datetime'],
                        'game_mode': game_mode,
                        'version': version,
                        'player_perspective': player_id,
                        'scraped_at': result.get('scraped_at'),
                        'players': players_list,
                        'map': result.get('map'),
                        'prelude_on': result.get('prelude_on'),
                        'colonies_on': result.get('colonies_on'),
                        'corporate_era_on': result.get('corporate_era_on'),
                        'draft_on': result.get('draft_on'),
                        'beginners_corporations_on': result.get('beginners_corporations_on'),
                        'game_speed': result.get('game_speed')
                    }
                    
                    # Upload to API
                    if api_client.update_single_game(game_api_data, indexed_by_email=config.BGA_EMAIL):
                        successful += 1
                        print(f"    [{i}/{len(new_games)}] ✅ Game {table_id} ({game_mode}) indexed")
                    else:
                        failed += 1
                        print(f"    [{i}/{len(new_games)}] ❌ Failed to upload game {table_id}")
                else:
                    failed += 1
                    print(f"    [{i}/{len(new_games)}] ❌ Failed to scrape game {table_id}")
                
            except Exception as e:
                failed += 1
                logger.error(f"Error processing game {table_id}: {e}")
                print(f"    [{i}/{len(new_games)}] ❌ Error processing game {table_id}: {e}")
            
            # Add delay between games
            if config.REQUEST_DELAY > 0:
                time.sleep(config.REQUEST_DELAY)
        
        print(f"  📊 Player {player_name}: {successful}/{len(new_games)} games indexed successfully")
        return successful, failed
        
    except Exception as e:
        logger.error(f"Error indexing games for player {player_id}: {e}")
        print(f"  ❌ Error indexing player {player_id}: {e}")
        return 0, 0


def main():
    """Main execution function"""
    print("\n" + "="*80)
    print("BGA TM Scraper - Index Top 100 Players")
    print("="*80)
    print(f"Version: {BUILD_VERSION}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Fetch players
        players = fetch_players()
        
        # Initialize API client
        api_client = APIClient(api_key=config.API_KEY, version=BUILD_VERSION)
        
        # Step 2: Update players via API
        update_players_via_api(api_client, players)
        
        # Step 3: Sort by Elo and get top 100
        print("\n" + "="*80)
        print("STEP 3: Indexing games for top 100 players by Elo")
        print("="*80)
        
        players_by_elo = sorted(players, key=lambda x: x['elo'], reverse=True)
        top_100 = players_by_elo[:50]
        # target_name = "StrandedKnight"
        # top_100 = [p for p in players_by_elo if p.get("name") == target_name]
        
        print(f"\nTop 100 players by Elo:")
        for i, player in enumerate(top_100, 1):
            print(f"  {i}. {player['name']} (Elo: {player['elo']}, ID: {player['playerId']})")
        
        # Initialize scraper
        scraper, parser = initialize_scraper()
        
        # Track overall stats
        total_successful = 0
        total_failed = 0
        players_processed = 0
        players_failed = 0
        
        # Index games for each player
        print("\n" + "="*80)
        print("Processing players...")
        print("="*80)
        
        for i, player in enumerate(top_100, 1):
            player_id = str(player['playerId'])
            player_name = player['name']
            
            print(f"\n[{i}/100] Processing {player_name} (Elo: {player['elo']})")
            
            try:
                successful, failed = index_games_for_player(
                    scraper, parser, api_client, player_id, player_name
                )
                total_successful += successful
                total_failed += failed
                players_processed += 1
            except Exception as e:
                logger.error(f"Failed to process player {player_name}: {e}")
                print(f"  ❌ Failed to process player: {e}")
                players_failed += 1
        
        # Close browser
        scraper.close_browser()
        
        # Final summary
        elapsed_time = datetime.now() - start_time
        
        print("\n" + "="*80)
        print("FINAL SUMMARY")
        print("="*80)
        print(f"Players processed: {players_processed}/100")
        print(f"Players failed: {players_failed}/100")
        print(f"Total games indexed: {total_successful}")
        print(f"Total games failed: {total_failed}")
        if total_successful + total_failed > 0:
            success_rate = (total_successful / (total_successful + total_failed)) * 100
            print(f"Success rate: {success_rate:.1f}%")
        print(f"Time elapsed: {str(elapsed_time).split('.')[0]}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
