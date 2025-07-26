#!/usr/bin/env python3
"""
Terraforming Mars BGA Scraper - Main CLI Interface
A comprehensive tool for scraping and parsing Terraforming Mars game data from BoardGameArena
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import configuration and modules
try:
    import config
    from bga_tm_scraper.scraper import TMScraper
    from bga_tm_scraper.parser import Parser
    from bga_tm_scraper.games_registry import GamesRegistry
    from bga_tm_scraper.bga_session import BGASession
    from gui.api_client import APIClient
    import requests
    import json
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    print("Please ensure all dependencies are installed and config.py is properly configured.")
    sys.exit(1)


def get_next_player_to_index() -> Optional[str]:
    """
    Get the next player ID to scrape from the API
    
    Returns:
        str: Player ID or None if no more players available
    """
    try:
        url = f"https://bga-tm-scraper-functions.azurewebsites.net/api/GetNextPlayerToIndex?code={config.API_KEY}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        player_id = data.get('playerId')
        
        if player_id:
            logger.info(f"Got next player from API: {player_id}")
            return str(player_id)
        else:
            logger.info("No more players available from API")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting next player from API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting next player: {e}")
        return None


def get_indexed_games_by_player(player_id: str) -> List[str]:
    """
    Get list of already indexed game table IDs for a player
    
    Args:
        player_id: Player ID to get indexed games for
        
    Returns:
        list: List of table IDs (strings) that are already indexed
    """
    try:
        url = f"https://bga-tm-scraper-functions.azurewebsites.net/api/GetIndexedGamesByPlayer?playerId={player_id}&code={config.API_KEY}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        table_ids = data
        
        logger.info(f"Found {len(table_ids)} indexed games for player {player_id}")
        return [str(tid) for tid in table_ids]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting indexed games for player {player_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting indexed games: {e}")
        return []


def update_single_game(game_data: Dict[str, Any]) -> bool:
    """
    POST a single game's data to the API
    
    Args:
        game_data: Dictionary containing the single game data to upload
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        url = f"https://bga-tm-scraper-functions.azurewebsites.net/api/UpdateSingleGame?code={config.API_KEY}"
        response = requests.post(url, json=game_data, timeout=60)
        response.raise_for_status()
        
        logger.info(f"Successfully updated single game {game_data.get('table_id')} for player {game_data.get('player_perspective')}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating single game via API: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating single game: {e}")
        return False


def update_games(api_data: Dict[str, Any]) -> bool:
    """
    POST the scraped games data to the API (legacy function for batch updates)
    
    Args:
        api_data: Dictionary containing the games data to upload
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        url = f"https://bga-tm-scraper-functions.azurewebsites.net/api/UpdateGames?code={config.API_KEY}"
        response = requests.post(url, json=api_data, timeout=60)
        response.raise_for_status()
        
        logger.info(f"Successfully updated games for player {api_data.get('player_id')}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating games via API: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating games: {e}")
        return False


def create_api_client() -> APIClient:
    """Create API client from config"""
    try:
        return APIClient(config.API_KEY)
    except Exception as e:
        logger.error(f"Failed to create API client: {e}")
        raise RuntimeError(f"API client initialization failed: {e}")


def upload_game_log_to_api(game_data: Dict[str, Any], api_client: APIClient) -> bool:
    """Upload parsed game data using store_game_log"""
    try:
        return api_client.store_game_log(game_data, config.BGA_EMAIL)
    except Exception as e:
        logger.error(f"Failed to upload game log to API: {e}")
        return False


def detect_argument_type(arg: str) -> str:
    """Detect if argument is player_id or composite_key"""
    if ':' in arg:
        return 'composite_key'
    elif arg.isdigit():
        return 'player_id'
    else:
        raise ValueError(f"Invalid argument format: {arg}")


def process_mixed_arguments(args: List[str]) -> Dict[str, List[str]]:
    """Separate player IDs from composite keys"""
    player_ids = []
    composite_keys = []
    
    for arg in args:
        try:
            if detect_argument_type(arg) == 'player_id':
                player_ids.append(arg)
            else:
                composite_keys.append(arg)
        except ValueError as e:
            logger.error(str(e))
            continue
    
    return {'player_ids': player_ids, 'composite_keys': composite_keys}


def validate_config():
    """Validate that configuration is properly set up"""
    required_attrs = ['BGA_EMAIL', 'BGA_PASSWORD', 'RAW_DATA_DIR', 'PARSED_DATA_DIR']
    
    for attr in required_attrs:
        if not hasattr(config, attr):
            logger.error(f"Missing required configuration: {attr}")
            return False
    
    if config.BGA_EMAIL == "your_email@example.com":
        logger.error("Please update BGA_EMAIL in config.py with your actual credentials")
        return False
    
    # ChromeDriver validation - now optional with webdriver-manager
    use_webdriver_manager = getattr(config, 'USE_WEBDRIVER_MANAGER', True)
    chromedriver_path = getattr(config, 'CHROMEDRIVER_PATH', None)
    
    if not use_webdriver_manager:
        # If webdriver-manager is disabled, require manual ChromeDriver path
        if not chromedriver_path:
            logger.error("CHROMEDRIVER_PATH is required when USE_WEBDRIVER_MANAGER is False")
            return False
        
        if not os.path.exists(chromedriver_path):
            logger.error(f"ChromeDriver not found at: {chromedriver_path}")
            return False
    
    # Check if webdriver-manager is available when needed
    if use_webdriver_manager and (not chromedriver_path or not os.path.exists(chromedriver_path)):
        try:
            import webdriver_manager
            logger.info("webdriver-manager is available for automatic ChromeDriver management")
        except ImportError:
            logger.error("webdriver-manager not installed. Please install it with: pip install webdriver-manager")
            logger.error("Or set USE_WEBDRIVER_MANAGER=False and provide a manual CHROMEDRIVER_PATH")
            return False
    
    return True


def parse_composite_keys(composite_keys: List[str]) -> List[Dict[str, str]]:
    """Parse composite keys in format table_id:player_perspective"""
    games = []
    for key in composite_keys:
        if ':' not in key:
            logger.error(f"Invalid composite key format: {key}. Expected format: table_id:player_perspective")
            continue
        
        table_id, player_perspective = key.split(':', 1)
        games.append({
            'table_id': table_id.strip(),
            'player_perspective': player_perspective.strip()
        })
    
    return games


def load_players_by_rank() -> List[Dict[str, Any]]:
    """Load players from players.csv ordered by ArenaRank"""
    import csv
    
    players = []
    players_file = os.path.join(config.REGISTRY_DATA_DIR, 'players.csv')
    
    try:
        with open(players_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                players.append({
                    'player_id': row['PlayerId'],
                    'player_name': row['PlayerName'],
                    'country': row['Country'],
                    'arena_rank': int(row['ArenaRank'])
                })
        
        players.sort(key=lambda x: x['arena_rank'])
        return players
    except FileNotFoundError:
        logger.error(f"Players file not found: {players_file}")
        return []
    except Exception as e:
        logger.error(f"Error loading players: {e}")
        return []


def is_player_discovery_completed(player_id: str) -> bool:
    """
    Check if a player has completed discovery by looking for complete_summary.json
    with discovery_completed = true
    
    Args:
        player_id: Player ID to check
        
    Returns:
        bool: True if discovery is completed, False otherwise
    """
    try:
        # Get processed data directory
        processed_dir = getattr(config, 'PROCESSED_DATA_DIR', 'data/processed')
        summary_file = os.path.join(processed_dir, player_id, 'complete_summary.json')
        
        if not os.path.exists(summary_file):
            return False
        
        # Load and check the summary file
        import json
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        # Check if discovery is completed
        discovery_completed = summary_data.get('discovery_completed', False)
        
        if discovery_completed:
            logger.debug(f"Player {player_id} has completed discovery")
            return True
        else:
            logger.debug(f"Player {player_id} discovery not completed")
            return False
            
    except Exception as e:
        logger.debug(f"Error checking discovery status for player {player_id}: {e}")
        return False


def update_players_registry(count: int = 1000) -> bool:
    """Update the players registry"""
    try:
        from bga_tm_scraper.leaderboard_scraper import LeaderboardScraper
        from bga_tm_scraper.players_registry import PlayersRegistry
        
        logger.info("Updating players registry...")
        
        # Initialize BGA session with smart ChromeDriver detection
        chromedriver_path = getattr(config, 'CHROMEDRIVER_PATH', None)
        session = BGASession(
            email=config.BGA_EMAIL,
            password=config.BGA_PASSWORD,
            chromedriver_path=chromedriver_path,
            chrome_path=getattr(config, 'CHROME_PATH', None),
            headless=True
        )
        
        if not session.login():
            logger.error("Failed to login to BGA for player update")
            return False
        
        # Fetch players data
        scraper = LeaderboardScraper(session)
        players_data = scraper.get_players_by_rank(config.TERRAFORMING_MARS_GAME_ID, count)
        
        if not players_data:
            logger.warning("No players data retrieved")
            return False
        
        # Update registry
        registry_path = os.path.join(config.REGISTRY_DATA_DIR, 'players.csv')
        registry = PlayersRegistry(registry_path)
        update_stats = registry.update_players(players_data)
        
        logger.info(f"Players registry updated: {update_stats['new_players']} new, "
                   f"{update_stats['updated_players']} updated, "
                   f"{update_stats['total_players']} total")
        
        session.close_browser()
        return True
        
    except Exception as e:
        logger.error(f"Error updating players registry: {e}")
        return False


def initialize_scraper() -> TMScraper:
    """Initialize and authenticate the scraper"""
    chromedriver_path = getattr(config, 'CHROMEDRIVER_PATH', None)
    scraper = TMScraper(
        chromedriver_path=chromedriver_path,
        chrome_path=getattr(config, 'CHROME_PATH', None),
        request_delay=getattr(config, 'REQUEST_DELAY', 1),
        headless=True,
        email=config.BGA_EMAIL,
        password=config.BGA_PASSWORD
    )
    
    if not scraper.start_browser_and_login():
        logger.error("Failed to start browser and login")
        raise RuntimeError("Authentication failed")
    
    return scraper


def process_single_game(table_id: str, player_perspective: str, scraper: TMScraper, games_registry: GamesRegistry, 
                        upload_to_api: bool = False, game_info: Dict[str, Any] = None) -> bool:
    """
    Process a single game - scrape table and store in local registry or upload to API
    
    Args:
        table_id: BGA table ID
        player_perspective: Player ID whose perspective this is from
        scraper: Initialized TMScraper instance
        games_registry: GamesRegistry instance for local storage
        upload_to_api: Whether to upload to API instead of local storage
        game_info: Optional game info dict with raw_datetime and parsed_datetime
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = scraper.scrape_table_only(table_id, player_perspective, save_raw=True, 
                                         raw_data_dir=config.RAW_DATA_DIR)
        
        if result and result.get('success'):
            game_mode = result.get('game_mode', 'Normal mode')
            map_name = result.get('map')
            corporate_era_on = result.get('corporate_era_on')
            prelude_on = result.get('prelude_on')
            draft_on = result.get('draft_on')
            colonies_on = result.get('colonies_on')
            beginners_corporations_on = result.get('beginners_corporations_on')
            game_speed = result.get('game_speed')
            elo_data = result.get('elo_data', {})
            version = result.get('version')
            
            # Convert EloData objects to dictionaries for JSON serialization
            players_list = []
            for player_name, elo_obj in elo_data.items():
                player_dict = {
                    'player_name': elo_obj.player_name or player_name,
                    'player_id': elo_obj.player_id,
                    'position': elo_obj.position,
                    'arena_points': elo_obj.arena_points,
                    'arena_points_change': elo_obj.arena_points_change,
                    'game_rank': elo_obj.game_rank,
                    'game_rank_change': elo_obj.game_rank_change
                }
                players_list.append(player_dict)
            
            # Create game data structure for single game API
            # Use extracted game date from table if available, otherwise fall back to game_info
            raw_datetime = 'unknown'
            parsed_datetime = None
            
            if result.get('game_date_info'):
                # Use date extracted from table HTML
                date_info = result['game_date_info']
                raw_datetime = date_info.get('raw_datetime', 'unknown')
                parsed_datetime = date_info.get('parsed_datetime')
            elif game_info:
                # Fall back to game_info (from player history)
                raw_datetime = game_info.get('raw_datetime', 'unknown')
                parsed_datetime = game_info.get('parsed_datetime')
            
            game_api_data = {
                'table_id': table_id,
                'raw_datetime': raw_datetime,
                'parsed_datetime': parsed_datetime,
                'game_mode': game_mode,
                'map': map_name,
                'corporate_era_on': corporate_era_on,
                'prelude_on': prelude_on,
                'draft_on': draft_on,
                'colonies_on': colonies_on,
                'beginners_corporations_on': beginners_corporations_on,
                'game_speed': game_speed,
                'version': version,
                'player_perspective': player_perspective,
                'scraped_at': result.get('scraped_at'),
                'players': players_list
            }
            
            if upload_to_api:
                # Upload to API
                if update_single_game(game_api_data):
                    logger.info(f"✅ Game {table_id} ({game_mode}) uploaded to API successfully")
                    print(f"✅ Uploaded game {table_id} ({game_mode}) to API")
                    if map_name:
                        print(f"   Map: {map_name}")
                    return True
                else:
                    logger.error(f"❌ Failed to upload game {table_id} to API")
                    print(f"❌ Failed to upload game {table_id} to API")
                    return False
            else:
                # Store in local registry
                is_arena_mode = game_mode == "Arena mode"
                
                # Extract player IDs from ELO data
                player_ids_found = [elo_obj.player_id for elo_obj in elo_data.values() if elo_obj.player_id]
                
                # Add to registry
                games_registry.add_game_check(
                    table_id=table_id,
                    raw_datetime=game_info.get('raw_datetime') if game_info else 'unknown',
                    parsed_datetime=game_info.get('parsed_datetime') if game_info else None,
                    players=player_ids_found,
                    is_arena_mode=is_arena_mode,
                    version=version,
                    player_perspective=player_perspective
                )
                
                logger.info(f"✅ Game {table_id} ({game_mode}) added to local registry")
                print(f"✅ Added game {table_id} ({game_mode}) to local registry")
                if map_name:
                    print(f"   Map: {map_name}")
                return True
        else:
            logger.warning(f"❌ Failed to scrape game {table_id}")
            print(f"❌ Failed to scrape game {table_id}")
            return False
    
    except Exception as e:
        logger.error(f"Error processing game {table_id}: {e}")
        print(f"❌ Error processing game {table_id}: {e}")
        return False


def process_single_player(player_id: str, scraper: TMScraper, args) -> None:
    """Indexes a single player's games - uses API for filtering and saving each game individually"""
    
    # Get already indexed games from API
    indexed_games = get_indexed_games_by_player(player_id)
    logger.info(f"Found {len(indexed_games)} already indexed games for player {player_id}")
    
    # Scrape player's game history
    games_data = scraper.scrape_player_game_history(
        player_id=player_id,
        max_clicks=1000,
    )
    
    if not games_data:
        logger.warning(f"No games found for player {player_id}")
        return
    
    # Process each game individually using the reusable method
    games_processed = 0
    games_indexed = 0
    
    for game_info in games_data:
        table_id = game_info['table_id']
        
        # TEMPORARY DON'T SKIP INDEXED GAMES
        
        # # Skip already indexed games
        # if table_id in indexed_games:
        #     logger.info(f"Skipping already indexed game {table_id}")
        #     continue
        
        games_registry = GamesRegistry()
        if process_single_game(table_id, player_id, scraper, games_registry, False, game_info):
            games_indexed += 1
        
        games_processed += 1
        
        # Add delay between games
        time.sleep(getattr(config, 'REQUEST_DELAY', 1))
    
    # Summary for this player
    if games_processed > 0:
        logger.info(f"Player {player_id} summary: {games_indexed}/{games_processed} games indexed successfully")
        print(f"📊 Player {player_id}: {games_indexed}/{games_processed} games indexed")
    else:
        logger.info(f"No new games to process for player {player_id}")
        print(f"ℹ️  No new games for player {player_id}")


def handle_scrape_tables(args) -> None:
    """Handle unified scrape-tables command (supports player IDs, composite keys, and API mode)"""
    logger.info("Starting table scraping...")
    
    # Determine processing mode based on arguments
    if args.players:
        # Process mixed arguments (player IDs and composite keys)
        processed_args = process_mixed_arguments(args.players)
        player_ids = processed_args['player_ids']
        composite_keys = processed_args['composite_keys']
        
        logger.info(f"Mixed mode: {len(player_ids)} player IDs, {len(composite_keys)} composite keys")
        
        # Initialize scraper
        scraper = initialize_scraper()
        
        try:
            # Process player IDs (scrape all games for these players)
            if player_ids:
                logger.info(f"Processing {len(player_ids)} player IDs")
                for i, player_id in enumerate(player_ids, 1):
                    logger.info(f"Processing player {i}/{len(player_ids)}: {player_id}")
                    process_single_player(player_id, scraper, args)
            
            # Process composite keys (scrape specific games)
            if composite_keys:
                logger.info(f"Processing {len(composite_keys)} composite keys")
                target_games = parse_composite_keys(composite_keys)
                
                if target_games:
                    successful_games = 0
                    failed_games = 0
                    
                    for i, game in enumerate(target_games, 1):
                        table_id = game['table_id']
                        player_perspective = game['player_perspective']
                        
                        logger.info(f"Processing game {i}/{len(target_games)}: table_id={table_id}, player_perspective={player_perspective}")
                        print(f"\n🎯 Processing game {i}/{len(target_games)}: {table_id} from perspective of player {player_perspective}")
                        
                        # Process the game
                        games_registry = GamesRegistry()
                        success = process_single_game(table_id, player_perspective, scraper, games_registry, args.upload_to_api)
                        
                        if success:
                            successful_games += 1
                            logger.info(f"✅ Successfully processed game {table_id}")
                            print(f"✅ Game {table_id} processed successfully!")
                        else:
                            failed_games += 1
                            logger.error(f"❌ Failed to process game {table_id}")
                            print(f"❌ Failed to process game {table_id}")
                        
                        # Add delay between games (except for the last one)
                        if i < len(target_games):
                            delay = getattr(config, 'REQUEST_DELAY', 1)
                            print(f"⏱️  Waiting {delay}s before next game...")
                            time.sleep(delay)
                    
                    # Summary for composite keys
                    logger.info(f"Composite key processing completed: {successful_games}/{len(target_games)} games processed successfully")
                    print(f"\n📊 Composite key summary: {successful_games}/{len(target_games)} games processed successfully")
                    if failed_games > 0:
                        print(f"❌ {failed_games} games failed")
                        
        finally:
            scraper.close_browser()
            
    else:
        # API mode: get players from API endpoint
        logger.info("API mode: Getting players from API endpoint")
        
        # Initialize scraper
        scraper = initialize_scraper()
        
        try:
            while True:
                player_id = get_next_player_to_index()
                if not player_id:
                    logger.info("No more players available from API")
                    break
                
                logger.info(f"Processing player from API: {player_id}")
                process_single_player(player_id, scraper, args)
        finally:
            scraper.close_browser()
    
    logger.info("Table scraping completed")


def handle_scrape_complete(args) -> None:
    """Handle scrape-complete command"""
    logger.info("Starting complete scraping workflow...")
    
    # Update players if requested
    if args.update_players:
        if not update_players_registry():
            logger.error("Failed to update players registry")
            return
    
    # Initialize API client if upload is requested
    api_client = None
    if args.upload_to_api:
        try:
            api_client = create_api_client()
            logger.info("API client initialized for game log uploads")
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            return

    # Determine target processing mode
    if args.all:
        # Process all players mode
        players = load_players_by_rank()
        if not players:
            logger.error("No players found. Run 'update-players' first.")
            return
        
        # Filter out players with completed discovery
        total_players = len(players)
        filtered_players = []
        completed_players = 0
        
        for player in players:
            player_id = player['player_id']
            if is_player_discovery_completed(player_id):
                completed_players += 1
                logger.debug(f"Skipping player {player_id} - discovery already completed")
            else:
                filtered_players.append(player)
        
        player_ids = [p['player_id'] for p in filtered_players]
        composite_keys = []
        
        logger.info(f"Found {total_players} total players")
        logger.info(f"Filtered out {completed_players} players with completed discovery")
        logger.info(f"Processing remaining {len(player_ids)} players")
        print(f"📊 Player filtering: {len(player_ids)}/{total_players} players to process ({completed_players} already completed)")
        
        if not player_ids:
            logger.info("No players need processing - all have completed discovery")
            print("✅ All players have completed discovery!")
            return
            
    elif args.players:
        # Process mixed arguments (player IDs and composite keys)
        processed_args = process_mixed_arguments(args.players)
        player_ids = processed_args['player_ids']
        composite_keys = processed_args['composite_keys']
        
        logger.info(f"Mixed mode: {len(player_ids)} player IDs, {len(composite_keys)} composite keys")
        
        if not player_ids and not composite_keys:
            logger.error("No valid arguments provided")
            return
    else:
        logger.error("Must specify either --all or provide player IDs/composite keys")
        return

    # Initialize components
    games_registry = GamesRegistry()
    scraper = initialize_scraper()
    parser = Parser()
    
    try:
        # Process player IDs (full workflow for each player)
        for i, player_id in enumerate(player_ids, 1):
            logger.info(f"Processing player {i}/{len(player_ids)}: {player_id}")
            
            # Scrape player's game history
            games_data = scraper.scrape_player_game_history(
                player_id=player_id,
                max_clicks=1000
            )
            
            if not games_data:
                logger.warning(f"No games found for player {player_id}")
                continue
            
            # Process each game (complete workflow)
            for game_info in games_data:
                table_id = game_info['table_id']
                
                # Skip if already processed and not retrying failed
                if not args.retry_failed and games_registry.is_game_parsed(table_id, player_id):
                    continue
                
                try:
                    result = scraper.scrape_table_and_replay(table_id, player_id, save_raw=True,
                                                           raw_data_dir=config.RAW_DATA_DIR)
                    
                    if result and result.get('success'):
                        is_arena_mode = result.get('arena_mode', False)
                        version = result.get('version')
                        
                        # Extract player IDs from scraped data
                        player_ids_found = []
                        if result.get('table_data') and result['table_data'].get('html_content'):
                            player_ids_found = scraper.extract_player_ids_from_table(
                                result['table_data']['html_content']
                            )
                        
                        # Add to registry and mark as scraped
                        games_registry.add_game_check(
                            table_id=table_id,
                            raw_datetime=game_info['raw_datetime'],
                            parsed_datetime=game_info['parsed_datetime'],
                            players=player_ids_found,
                            is_arena_mode=is_arena_mode,
                            version=version,
                            player_perspective=player_id
                        )
                        games_registry.mark_game_scraped(table_id, player_perspective=player_id)
                        
                        # Parse the game using new unified method
                        table_html = result['table_data']['html_content']
                        replay_html = result['replay_data'].get('html_content', '')
                        
                        if replay_html:
                            # Parse table metadata first
                            game_metadata = parser.parse_table_metadata(table_html)
                            
                            # Add version if available
                            if version:
                                game_metadata.version_id = version
                            
                            game_data = parser.parse_complete_game(
                                replay_html=replay_html,
                                game_metadata=game_metadata,
                                table_id=table_id,
                                player_perspective=player_id
                            )
                            
                            # Export to JSON
                            output_path = os.path.join(config.PARSED_DATA_DIR, f"game_{table_id}.json")
                            parser.export_to_json(game_data, output_path, player_perspective=player_id)
                            
                            # Upload to API if requested
                            if api_client:
                                try:
                                    # Convert GameData to API format
                                    api_format_data = parser._convert_game_data_to_api_format(game_data, table_id, player_id)
                                    if upload_game_log_to_api(api_format_data, api_client):
                                        logger.info(f"✅ Successfully uploaded game {table_id} to API")
                                        print(f"📤 Uploaded game {table_id} to API")
                                    else:
                                        logger.warning(f"⚠️ Failed to upload game {table_id} to API")
                                        print(f"❌ Failed to upload game {table_id} to API")
                                except Exception as upload_error:
                                    logger.error(f"Error uploading game {table_id} to API: {upload_error}")
                                    print(f"❌ Error uploading game {table_id} to API: {upload_error}")
                            
                            # Mark as parsed
                            games_registry.mark_game_parsed(table_id, player_perspective=player_id)
                            
                            game_mode_text = "Arena" if is_arena_mode else "Normal"
                            logger.info(f"✅ Successfully processed {game_mode_text} mode game {table_id}")
                        else:
                            logger.warning(f"⚠️  No replay data for game {table_id}")
                    else:
                        logger.warning(f"❌ Failed to scrape game {table_id}")
                
                except Exception as e:
                    logger.error(f"Error processing game {table_id}: {e}")
                
                # Add delay between games
                time.sleep(getattr(config, 'REQUEST_DELAY', 1))
            
            # Save registry after each player
            games_registry.save_registry()
        
        # Process composite keys (specific games)
        if composite_keys:
            logger.info(f"Processing {len(composite_keys)} composite keys")
            target_games = parse_composite_keys(composite_keys)
            
            if target_games:
                successful_games = 0
                failed_games = 0
                
                for i, game in enumerate(target_games, 1):
                    table_id = game['table_id']
                    player_perspective = game['player_perspective']
                    
                    logger.info(f"Processing composite key game {i}/{len(target_games)}: table_id={table_id}, player_perspective={player_perspective}")
                    print(f"\n🎯 Processing game {i}/{len(target_games)}: {table_id} from perspective of player {player_perspective}")
                    
                    # Skip if already processed and not retrying failed
                    if not args.retry_failed and games_registry.is_game_parsed(table_id, player_perspective):
                        logger.info(f"Skipping already parsed game {table_id}")
                        print(f"⏭️ Skipping already parsed game {table_id}")
                        continue
                    
                    try:
                        result = scraper.scrape_table_and_replay(table_id, player_perspective, save_raw=True,
                                                               raw_data_dir=config.RAW_DATA_DIR)
                        
                        if result and result.get('success'):
                            is_arena_mode = result.get('arena_mode', False)
                            version = result.get('version')
                            
                            # Extract player IDs from scraped data
                            player_ids_found = []
                            if result.get('table_data') and result['table_data'].get('html_content'):
                                player_ids_found = scraper.extract_player_ids_from_table(
                                    result['table_data']['html_content']
                                )
                            
                            # Add to registry and mark as scraped
                            games_registry.add_game_check(
                                table_id=table_id,
                                raw_datetime='unknown',  # No game_info for composite keys
                                parsed_datetime=None,
                                players=player_ids_found,
                                is_arena_mode=is_arena_mode,
                                version=version,
                                player_perspective=player_perspective
                            )
                            games_registry.mark_game_scraped(table_id, player_perspective=player_perspective)
                            
                            # Parse the game using new unified method
                            table_html = result['table_data']['html_content']
                            replay_html = result['replay_data'].get('html_content', '')
                            
                            if replay_html:
                                # Parse table metadata first
                                game_metadata = parser.parse_table_metadata(table_html)
                                
                                # Add version if available
                                if version:
                                    game_metadata.version_id = version
                                
                                game_data = parser.parse_complete_game(
                                    replay_html=replay_html,
                                    game_metadata=game_metadata,
                                    table_id=table_id,
                                    player_perspective=player_perspective
                                )
                                
                                # Export to JSON
                                output_path = os.path.join(config.PARSED_DATA_DIR, f"game_{table_id}.json")
                                parser.export_to_json(game_data, output_path, player_perspective=player_perspective)
                                
                                # Upload to API if requested
                                if api_client:
                                    try:
                                        # Convert GameData to API format
                                        api_format_data = parser._convert_game_data_to_api_format(game_data, table_id, player_perspective)
                                        if upload_game_log_to_api(api_format_data, api_client):
                                            logger.info(f"✅ Successfully uploaded game {table_id} to API")
                                            print(f"📤 Uploaded game {table_id} to API")
                                        else:
                                            logger.warning(f"⚠️ Failed to upload game {table_id} to API")
                                            print(f"❌ Failed to upload game {table_id} to API")
                                    except Exception as upload_error:
                                        logger.error(f"Error uploading game {table_id} to API: {upload_error}")
                                        print(f"❌ Error uploading game {table_id} to API: {upload_error}")
                                
                                # Mark as parsed
                                games_registry.mark_game_parsed(table_id, player_perspective=player_perspective)
                                
                                successful_games += 1
                                game_mode_text = "Arena" if is_arena_mode else "Normal"
                                logger.info(f"✅ Successfully processed {game_mode_text} mode game {table_id}")
                                print(f"✅ Game {table_id} processed successfully!")
                            else:
                                failed_games += 1
                                logger.warning(f"⚠️  No replay data for game {table_id}")
                                print(f"❌ No replay data for game {table_id}")
                        else:
                            failed_games += 1
                            logger.warning(f"❌ Failed to scrape game {table_id}")
                            print(f"❌ Failed to scrape game {table_id}")
                    
                    except Exception as e:
                        failed_games += 1
                        logger.error(f"Error processing game {table_id}: {e}")
                        print(f"❌ Error processing game {table_id}: {e}")
                    
                    # Add delay between games (except for the last one)
                    if i < len(target_games):
                        delay = getattr(config, 'REQUEST_DELAY', 1)
                        print(f"⏱️  Waiting {delay}s before next game...")
                        time.sleep(delay)
                
                # Summary for composite keys
                logger.info(f"Composite key processing completed: {successful_games}/{len(target_games)} games processed successfully")
                print(f"\n📊 Composite key summary: {successful_games}/{len(target_games)} games processed successfully")
                if failed_games > 0:
                    print(f"❌ {failed_games} games failed")
                
                # Save registry after composite key processing
                games_registry.save_registry()
    
    finally:
        scraper.close_browser()
    
    logger.info("Complete scraping workflow finished")


def handle_scrape_replays(args) -> None:
    """Handle scrape-replays command"""
    logger.info("Starting replay scraping...")
    
    # Initialize API client if upload is requested
    api_client = None
    if args.upload_to_api:
        try:
            api_client = create_api_client()
            logger.info("API client initialized for game log uploads")
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            return
    
    # Initialize session tracking and email notifications
    from bga_tm_scraper.session_tracker import start_new_session, end_current_session
    from bga_tm_scraper.email_notifier import create_email_notifier_from_config
    
    session_tracker = start_new_session()
    email_notifier = create_email_notifier_from_config()
    
    games_registry = GamesRegistry()
    
    # Determine target games
    if args.games:
        # Specific games provided
        target_games = parse_composite_keys(args.games)
        if not target_games:
            logger.error("No valid composite keys provided")
            return
        logger.info(f"Processing {len(target_games)} specified games")
    else:
        # Default: all scraped tables that need replay processing
        all_games = games_registry.get_all_games()
        target_games = []
        
        for composite_key, game_data in all_games.items():
            # Include games that have table HTML but missing replay or parsing
            if (game_data.get('is_arena_mode', False) and 
                (not game_data.get('scraped_at') or not game_data.get('parsed_at'))):
                target_games.append({
                    'table_id': game_data['table_id'],
                    'player_perspective': game_data.get('player_perspective')
                })
        
        logger.info(f"Found {len(target_games)} games needing replay processing")
    
    if not target_games:
        logger.info("No games to process")
        return
    
    # Initialize scraper for replay processing
    scraper = initialize_scraper()
    parser = Parser()
    
    try:
        successful_scrapes = 0
        successful_parses = 0
        
        for i, game in enumerate(target_games, 1):
            table_id = game['table_id']
            player_perspective = game['player_perspective']
            
            logger.info(f"Processing game {i}/{len(target_games)}: {table_id}")
            
            try:
                # Check if table HTML exists
                if player_perspective:
                    player_raw_dir = os.path.join(config.RAW_DATA_DIR, player_perspective)
                    table_html_path = os.path.join(player_raw_dir, f"table_{table_id}.html")
                    replay_html_path = os.path.join(player_raw_dir, f"replay_{table_id}.html")
                else:
                    table_html_path = os.path.join(config.RAW_DATA_DIR, f"table_{table_id}.html")
                    replay_html_path = os.path.join(config.RAW_DATA_DIR, f"replay_{table_id}.html")
                
                if not os.path.exists(table_html_path):
                    logger.warning(f"Table HTML not found: {table_html_path}")
                    continue
                
                # Read table HTML to get player IDs and version
                with open(table_html_path, 'r', encoding='utf-8') as f:
                    table_html = f.read()
                
                # Get version from registry first (optimization)
                game_info = games_registry.get_game_info(table_id, player_perspective)
                
                version = game_info.get('version') if game_info else None
                
                if version:
                    logger.info(f"Using cached version from registry: {version}")
                else:
                    logger.info("Version not in registry, extracting from gamereview...")
                    version = scraper.extract_version_from_gamereview(table_id)
                    if version and game_info:
                        # Update registry with the newly found version
                        game_info['version'] = version
                        games_registry.save_registry()
                        logger.info(f"Cached version {version} to registry for future use")
                
                if not version:
                    logger.warning(f"No version found for {table_id}")
                    continue
                
                # Check if replay already exists
                if os.path.exists(replay_html_path):
                    logger.info(f"Replay HTML already exists for {table_id}")
                    replay_exists = True
                else:
                    # Scrape replay only (table HTML already exists)
                    replay_result = scraper.scrape_replay_from_table(table_id, player_perspective, save_raw=True,
                                                                   raw_data_dir=config.RAW_DATA_DIR, version_id=version, 
                                                                   player_perspective=player_perspective)
                    
                    if replay_result:
                        # Check if replay limit was reached
                        if replay_result.get('limit_reached'):
                            session_tracker.set_termination_reason("Daily replay limit reached")
                            logger.warning("🚫 Daily replay limit reached - stopping scraping")
                            print("\n" + "="*60)
                            print("🚫 DAILY REPLAY LIMIT REACHED")
                            print("BGA has daily limits on replay access to prevent server overload.")
                            print("Please try again tomorrow or wait for the limit to reset.")
                            print(f"Progress: {successful_scrapes} replays scraped, {successful_parses} games parsed")
                            print("="*60)
                            break  # Exit the game processing loop
                        
                        successful_scrapes += 1
                        session_tracker.increment_successful_scrapes()
                        replay_exists = True
                        logger.info(f"✅ Successfully scraped replay for {table_id}")
                    else:
                        session_tracker.increment_failed_operations()
                        session_tracker.add_error(f"Failed to scrape replay for game {table_id}")
                        logger.warning(f"❌ Failed to scrape replay for {table_id}")
                        continue
                
                # Parse the game if both HTMLs exist
                if replay_exists and os.path.exists(replay_html_path):
                    with open(replay_html_path, 'r', encoding='utf-8') as f:
                        replay_html = f.read()
                    
                    game_data = parser.parse_complete_game_with_elo(
                        replay_html=replay_html,
                        table_html=table_html,
                        table_id=table_id,
                        player_perspective=player_perspective
                    )
                    
                    # Export to JSON
                    output_path = os.path.join(config.PARSED_DATA_DIR, f"game_{table_id}.json")
                    parser.export_to_json(game_data, output_path, player_perspective=player_perspective)
                    
                    # Upload to API if requested
                    if api_client:
                        try:
                            # Convert GameData to API format
                            api_format_data = parser._convert_game_data_to_api_format(game_data, table_id, player_perspective)
                            if upload_game_log_to_api(api_format_data, api_client):
                                logger.info(f"✅ Successfully uploaded game {table_id} to API")
                                print(f"📤 Uploaded game {table_id} to API")
                            else:
                                logger.warning(f"⚠️ Failed to upload game {table_id} to API")
                                print(f"❌ Failed to upload game {table_id} to API")
                        except Exception as upload_error:
                            logger.error(f"Error uploading game {table_id} to API: {upload_error}")
                            print(f"❌ Error uploading game {table_id} to API: {upload_error}")
                    
                    # Mark as scraped and parsed
                    games_registry.mark_game_scraped(table_id, player_perspective=player_perspective)
                    games_registry.mark_game_parsed(table_id, player_perspective=player_perspective)
                    
                    # Save registry after each successful parse to prevent data loss
                    logger.info(f"Attempting to save registry to: {games_registry.registry_path}")
                    try:
                        # Check if directory exists and is writable
                        registry_dir = os.path.dirname(games_registry.registry_path)
                        if not os.path.exists(registry_dir):
                            logger.error(f"Registry directory does not exist: {registry_dir}")
                            os.makedirs(registry_dir, exist_ok=True)
                            logger.info(f"Created registry directory: {registry_dir}")
                        
                        # Check if file is writable
                        if os.path.exists(games_registry.registry_path):
                            if not os.access(games_registry.registry_path, os.W_OK):
                                logger.error(f"Registry file is not writable: {games_registry.registry_path}")
                            else:
                                logger.info(f"Registry file is writable: {games_registry.registry_path}")
                        
                        # Attempt to save
                        games_registry.save_registry()
                        logger.info(f"✅ Registry saved successfully for game {table_id}")
                        
                        # Verify the save worked by checking file modification time
                        if os.path.exists(games_registry.registry_path):
                            mtime = os.path.getmtime(games_registry.registry_path)
                            mtime_str = datetime.fromtimestamp(mtime).isoformat()
                            logger.info(f"Registry file last modified: {mtime_str}")
                        else:
                            logger.error(f"❌ Registry file does not exist after save attempt!")
                            
                    except Exception as save_error:
                        logger.error(f"❌ Failed to save registry for game {table_id}: {save_error}")
                        logger.error(f"Registry path: {games_registry.registry_path}")
                        logger.error(f"Registry data keys: {list(games_registry.registry_data.keys())}")
                    
                    successful_parses += 1
                    session_tracker.increment_successful_parses()
                    logger.info(f"✅ Successfully parsed game {table_id}")
            
            except Exception as e:
                session_tracker.add_error(f"Error processing game {table_id}: {str(e)}", context=f"Game: {table_id}")
                logger.error(f"Error processing game {table_id}: {e}")
            
            # Add delay between games
            time.sleep(getattr(config, 'REQUEST_DELAY', 1))
        
        # Determine termination reason if not already set
        if not session_tracker.termination_reason:
            if successful_scrapes == 0 and successful_parses == 0:
                session_tracker.set_termination_reason("No games processed - all games already completed or no games found")
            else:
                session_tracker.set_termination_reason("All available games processed successfully")
        
        logger.info(f"Replay scraping complete: {successful_scrapes} scraped, {successful_parses} parsed")
        
    except Exception as e:
        session_tracker.add_error(f"Critical error in replay scraping: {str(e)}")
        session_tracker.set_termination_reason(f"Error encountered: {str(e)}")
        logger.error(f"Error in replay scraping: {e}")
    finally:
        scraper.close_browser()
        # Ensure registry is saved even if there were errors
        games_registry.save_registry()
        
        # End session and send email notification
        session_tracker = end_current_session()
        if session_tracker and email_notifier:
            try:
                # Get final statistics
                session_stats = session_tracker.get_session_stats()
                registry_stats = games_registry.get_stats()
                
                # Check config for email notification settings
                should_send_email = False
                termination_reason = session_stats.get('termination_reason', 'Unknown')
                
                if hasattr(config, 'EMAIL_ON_DAILY_LIMIT') and config.EMAIL_ON_DAILY_LIMIT:
                    if 'limit reached' in termination_reason.lower():
                        should_send_email = True
                
                if hasattr(config, 'EMAIL_ON_COMPLETION') and config.EMAIL_ON_COMPLETION:
                    if 'successfully' in termination_reason.lower() or 'processed' in termination_reason.lower():
                        should_send_email = True
                
                if hasattr(config, 'EMAIL_ON_ERROR') and config.EMAIL_ON_ERROR:
                    if 'error' in termination_reason.lower():
                        should_send_email = True
                
                if should_send_email:
                    logger.info("Sending email notification...")
                    success = email_notifier.send_scraping_completion_email(
                        termination_reason=termination_reason,
                        session_stats=session_stats,
                        registry_stats=registry_stats,
                        start_time=session_tracker.start_time,
                        end_time=session_tracker.end_time
                    )
                    
                    if success:
                        logger.info("✅ Email notification sent successfully")
                    else:
                        logger.warning("⚠️ Failed to send email notification")
                else:
                    logger.info("Email notifications disabled or not configured for this termination reason")
                    
            except Exception as email_error:
                logger.error(f"Error sending email notification: {email_error}")


def handle_parse(args) -> None:
    """Handle parse command"""
    logger.info("Starting game parsing...")
    
    # Initialize API client if upload is requested
    api_client = None
    if args.upload_to_api:
        try:
            api_client = create_api_client()
            logger.info("API client initialized for game log uploads")
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            return
    
    games_registry = GamesRegistry()
    parser = Parser()
    
    # Determine target games
    if args.games:
        # Specific games provided
        target_games = parse_composite_keys(args.games)
        if not target_games:
            logger.error("No valid composite keys provided")
            return
        logger.info(f"Processing {len(target_games)} specified games")
    else:
        # Default: all games ready for parsing (have both table and replay HTML)
        all_games = games_registry.get_all_games()
        target_games = []
        
        for composite_key, game_data in all_games.items():
            table_id = game_data['table_id']
            player_perspective = game_data.get('player_perspective')
            
            # Determine if we should include this game
            should_include = False
            
            if args.reparse:
                # With --reparse: include all Arena games that have been scraped (regardless of parsed status)
                should_include = (game_data.get('scraped_at') and game_data.get('is_arena_mode', False))
            else:
                # Without --reparse: only include games that are scraped but not parsed
                should_include = (game_data.get('scraped_at') and not game_data.get('parsed_at') and 
                                game_data.get('is_arena_mode', False))
            
            if should_include:
                # Verify both HTML files exist
                if player_perspective:
                    player_raw_dir = os.path.join(config.RAW_DATA_DIR, player_perspective)
                    table_html_path = os.path.join(player_raw_dir, f"table_{table_id}.html")
                    replay_html_path = os.path.join(player_raw_dir, f"replay_{table_id}.html")
                else:
                    table_html_path = os.path.join(config.RAW_DATA_DIR, f"table_{table_id}.html")
                    replay_html_path = os.path.join(config.RAW_DATA_DIR, f"replay_{table_id}.html")
                
                if os.path.exists(table_html_path) and os.path.exists(replay_html_path):
                    target_games.append({
                        'table_id': table_id,
                        'player_perspective': player_perspective,
                        'table_html_path': table_html_path,
                        'replay_html_path': replay_html_path
                    })
        
        if args.reparse:
            logger.info(f"Found {len(target_games)} games ready for reparsing (including already parsed)")
        else:
            logger.info(f"Found {len(target_games)} games ready for parsing")
    
    if not target_games:
        logger.info("No games to parse")
        return
    
    # Parse each game
    successful_parses = 0
    for i, game in enumerate(target_games, 1):
        table_id = game['table_id']
        player_perspective = game['player_perspective']
        
        if args.reparse:
            # Check if this game was already parsed
            game_info = games_registry.get_game_info(table_id, player_perspective)
            if game_info and game_info.get('parsed_at'):
                logger.info(f"Reparsing game {i}/{len(target_games)}: {table_id} (previously parsed)")
            else:
                logger.info(f"Parsing game {i}/{len(target_games)}: {table_id}")
        else:
            logger.info(f"Parsing game {i}/{len(target_games)}: {table_id}")
        
        try:
            # Determine HTML file paths if not provided
            if 'table_html_path' not in game:
                if player_perspective:
                    player_raw_dir = os.path.join(config.RAW_DATA_DIR, player_perspective)
                    table_html_path = os.path.join(player_raw_dir, f"table_{table_id}.html")
                    replay_html_path = os.path.join(player_raw_dir, f"replay_{table_id}.html")
                else:
                    table_html_path = os.path.join(config.RAW_DATA_DIR, f"table_{table_id}.html")
                    replay_html_path = os.path.join(config.RAW_DATA_DIR, f"replay_{table_id}.html")
            else:
                table_html_path = game['table_html_path']
                replay_html_path = game['replay_html_path']
            
            # Read HTML files
            if not os.path.exists(table_html_path):
                logger.warning(f"Table HTML not found: {table_html_path}")
                continue
            
            if not os.path.exists(replay_html_path):
                logger.warning(f"Replay HTML not found: {replay_html_path}")
                continue
            
            with open(table_html_path, 'r', encoding='utf-8') as f:
                table_html = f.read()
            
            with open(replay_html_path, 'r', encoding='utf-8') as f:
                replay_html = f.read()
            
            # Parse the game
            game_data = parser.parse_complete_game_with_elo(
                replay_html=replay_html,
                table_html=table_html,
                table_id=table_id,
                player_perspective=player_perspective or "unknown"
            )
            
            # Export to JSON
            output_path = os.path.join(config.PARSED_DATA_DIR, f"game_{table_id}.json")
            parser.export_to_json(game_data, output_path, player_perspective=player_perspective)
            
            # Upload to API if requested
            if api_client:
                try:
                    # Convert GameData to API format
                    api_format_data = parser._convert_game_data_to_api_format(game_data, table_id, player_perspective or "unknown")
                    if upload_game_log_to_api(api_format_data, api_client):
                        logger.info(f"✅ Successfully uploaded game {table_id} to API")
                        print(f"📤 Uploaded game {table_id} to API")
                    else:
                        logger.warning(f"⚠️ Failed to upload game {table_id} to API")
                        print(f"❌ Failed to upload game {table_id} to API")
                except Exception as upload_error:
                    logger.error(f"Error uploading game {table_id} to API: {upload_error}")
                    print(f"❌ Error uploading game {table_id} to API: {upload_error}")
            
            # Mark as parsed in registry
            games_registry.mark_game_parsed(table_id, player_perspective=player_perspective)
            
            successful_parses += 1
            logger.info(f"✅ Successfully parsed game {table_id}")
            
        except Exception as e:
            logger.error(f"❌ Error parsing game {table_id}: {e}")
    
    # Save updated registry
    games_registry.save_registry()
    
    logger.info(f"Parsing complete: {successful_parses}/{len(target_games)} games successfully parsed")


def handle_update_players(args) -> None:
    """Handle update-players command"""
    count = args.count if args.count else getattr(config, 'TOP_N_PLAYERS', 1000)

    if update_players_registry(count):
        logger.info("Players registry updated successfully")
    else:
        logger.error("Failed to update players registry")


def handle_status(args) -> None:
    """Handle status command"""
    logger.info("Checking registry status...")
    
    games_registry = GamesRegistry()
    games_registry.print_stats()
    
    if args.detailed:
        # Show additional detailed statistics
        all_games = games_registry.get_all_games()
        
        # Count by player perspective
        player_perspectives = {}
        for game_data in all_games.values():
            perspective = game_data.get('player_perspective', 'unknown')
            player_perspectives[perspective] = player_perspectives.get(perspective, 0) + 1
        
        print(f"\n=== Games by Player Perspective ===")
        for perspective, count in sorted(player_perspectives.items()):
            print(f"{perspective}: {count} games")
        
        # Show recent activity
        recent_scraped = []
        recent_parsed = []
        
        for game_data in all_games.values():
            if game_data.get('scraped_at'):
                recent_scraped.append((game_data['table_id'], game_data['scraped_at']))
            if game_data.get('parsed_at'):
                recent_parsed.append((game_data['table_id'], game_data['parsed_at']))
        
        recent_scraped.sort(key=lambda x: x[1], reverse=True)
        recent_parsed.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n=== Recent Activity ===")
        print("Last 5 scraped games:")
        for table_id, timestamp in recent_scraped[:5]:
            print(f"  {table_id}: {timestamp}")
        
        print("Last 5 parsed games:")
        for table_id, timestamp in recent_parsed[:5]:
            print(f"  {table_id}: {timestamp}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Terraforming Mars BGA Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Table scraping (indexing only)
  python main.py scrape-tables                                             # API mode - gets players from API
  python main.py scrape-tables 12345678 87654321                           # Player mode - specific players
  python main.py scrape-tables 670153426:91334215                          # Composite key mode - single game
  python main.py scrape-tables 670153426:91334215 665079560:86296239       # Composite key mode - multiple games
  python main.py scrape-tables 12345678 670153426:91334215                 # Mixed mode - player ID + composite key
  python main.py scrape-tables --upload-to-api 12345678                    # Upload table metadata to API
  python main.py scrape-tables --upload-to-api 670153426:91334215          # Composite key + API upload

  # Complete workflow (tables + replays + parsing)
  python main.py scrape-complete --all                                     # Process all players
  python main.py scrape-complete 12345678 87654321                         # Specific players
  python main.py scrape-complete 670153426:91334215                        # Single game via composite key
  python main.py scrape-complete 670153426:91334215 665079560:86296239     # Multiple games via composite keys
  python main.py scrape-complete --upload-to-api 12345678                  # Upload parsed games to API
  python main.py scrape-complete --upload-to-api 670153426:91334215        # Composite key + API upload

  # Replay scraping and parsing
  python main.py scrape-replays                                            # All games needing replays
  python main.py scrape-replays 670153426:91334215 665079560:86296239      # Specific games
  python main.py scrape-replays --upload-to-api                            # Upload parsed games to API

  # Parsing only
  python main.py parse                                                     # All games ready for parsing
  python main.py parse --reparse                                           # Reparse already parsed games
  python main.py parse --upload-to-api 670153426:91334215                  # Parse specific game + upload to API

  # Utility commands
  python main.py update-players --count 500                                # Update player registry
  python main.py status --detailed                                         # Show detailed registry status
        """
    )
    
    # Global options
    parser.add_argument('--retry-failed', action='store_true',
                       help='Include previously failed games')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # scrape-tables command (unified - supports player IDs, composite keys, and API mode)
    scrape_tables_parser = subparsers.add_parser('scrape-tables', 
                                                help='Scrape tables and update local registry (supports player IDs, composite keys, and API mode)')
    scrape_tables_parser.add_argument('--upload-to-api', action='store_true',
                                     help='Upload table metadata to API using update_single_game')
    scrape_tables_parser.add_argument('players', nargs='*',
                                     help='Space-separated list of player IDs or composite keys (table_id:player_perspective). If none provided, uses API mode.')
    
    # scrape-complete command
    scrape_complete_parser = subparsers.add_parser('scrape-complete',
                                                  help='Full workflow (tables + replays + parsing)')
    scrape_complete_parser.add_argument('--all', '-a', action='store_true',
                                       help='Process all players')
    scrape_complete_parser.add_argument('--update-players', action='store_true',
                                       help='Update player registry before processing')
    scrape_complete_parser.add_argument('--upload-to-api', action='store_true',
                                       help='Upload parsed games to API using store_game_log')
    scrape_complete_parser.add_argument('players', nargs='*',
                                       help='Space-separated list of player IDs or composite keys (table_id:player_perspective)')
    
    # scrape-replays command
    scrape_replays_parser = subparsers.add_parser('scrape-replays',
                                                 help='Scrape replays and parse (requires table HTMLs)')
    scrape_replays_parser.add_argument('--upload-to-api', action='store_true',
                                      help='Upload parsed games to API using store_game_log')
    scrape_replays_parser.add_argument('games', nargs='*',
                                      help='Space-separated list of composite keys (table_id:player_perspective)')
    
    # parse command
    parse_parser = subparsers.add_parser('parse',
                                        help='Parse games only (requires both HTMLs)')
    parse_parser.add_argument('--reparse', action='store_true',
                             help='Reparse already parsed games (overwrite existing JSON files)')
    parse_parser.add_argument('--upload-to-api', action='store_true',
                             help='Upload parsed games to API using store_game_log')
    parse_parser.add_argument('games', nargs='*',
                             help='Space-separated list of composite keys (table_id:player_perspective)')
    
    # update-players command
    update_players_parser = subparsers.add_parser('update-players',
                                                 help='Update player registry')
    update_players_parser.add_argument('--count', type=int,
                                      help='Number of top players to fetch')
    
    # status command
    status_parser = subparsers.add_parser('status',
                                         help='Show registry status')
    status_parser.add_argument('--detailed', action='store_true',
                              help='Show detailed statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Validate configuration
    if not validate_config():
        sys.exit(1)
    
    # Create data directories
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    os.makedirs(config.PARSED_DATA_DIR, exist_ok=True)
    os.makedirs(getattr(config, 'REGISTRY_DATA_DIR', 'data/registry'), exist_ok=True)
    
    # Route to appropriate handler
    try:
        if args.command == 'scrape-tables':
            handle_scrape_tables(args)
        elif args.command == 'scrape-complete':
            handle_scrape_complete(args)
        elif args.command == 'scrape-replays':
            handle_scrape_replays(args)
        elif args.command == 'parse':
            handle_parse(args)
        elif args.command == 'update-players':
            handle_update_players(args)
        elif args.command == 'status':
            handle_status(args)
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
