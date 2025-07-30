"""
In-memory scraper wrapper for BGA TM Scraper GUI
Handles scraping operations without saving files locally
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class InMemoryScraper:
    """Wrapper for TMScraper that works entirely in memory"""
    
    def __init__(self, config_manager, config_dict: Dict[str, Any], progress_callback: Optional[Callable] = None):
        """
        Initialize in-memory scraper
        
        Args:
            config_manager: The configuration manager instance.
            config_dict: Configuration dictionary from GUI
            progress_callback: Optional callback for progress updates
        """
        self.config_manager = config_manager
        self.config_dict = config_dict
        self.progress_callback = progress_callback
        self.scraper = None
        self.parser = None
        
        # Convert GUI config to scraper format
        self.scraper_config = self._convert_config_to_scraper_format(config_dict)
        
        # Initialize components
        self._initialize_components()
    
    def _convert_config_to_scraper_format(self, gui_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert GUI JSON config to format expected by scraper
        
        Args:
            gui_config: GUI configuration dictionary
            
        Returns:
            dict: Configuration in scraper format
        """
        try:
            scraper_config = {
                'BGA_EMAIL': gui_config.get('bga_credentials', {}).get('email', ''),
                'BGA_PASSWORD': gui_config.get('bga_credentials', {}).get('password', ''),
                'CHROME_PATH': gui_config.get('chrome_settings', {}).get('chrome_path', ''),
                'CHROMEDRIVER_PATH': gui_config.get('chrome_settings', {}).get('chromedriver_path', ''),
                'API_KEY': gui_config.get('api_settings', {}).get('api_key', ''),
                'TERRAFORMING_MARS_GAME_ID': 167791,  # Fixed game ID for TM
                'TABLE_URL_TEMPLATE': 'https://boardgamearena.com/table?table={table_id}',
                'REPLAY_URL_TEMPLATE': 'https://boardgamearena.com/archive/replay/{version_id}/?table={table_id}&player={player_id}&comments={player_id}',
                'REQUEST_DELAY': gui_config.get('scraping_settings', {}).get('request_delay', 1),
                'USE_WEBDRIVER_MANAGER': True,  # Default to using webdriver manager
                'RAW_DATA_DIR': None,  # Not used in memory mode
                'PARSED_DATA_DIR': None,  # Not used in memory mode
            }
            
            # Handle speed profile
            speed_profile = gui_config.get('scraping_settings', {}).get('speed_profile', 'NORMAL')
            if speed_profile == 'FAST':
                scraper_config['CURRENT_SPEED'] = {
                    "page_load_delay": 0.5,
                    "click_delay": 0.2,
                    "gamereview_delay": 0.5,
                    "element_wait_timeout": 3
                }
            elif speed_profile == 'SLOW':
                scraper_config['CURRENT_SPEED'] = {
                    "page_load_delay": 3,
                    "click_delay": 1,
                    "gamereview_delay": 3,
                    "element_wait_timeout": 10
                }
            else:  # NORMAL
                scraper_config['CURRENT_SPEED'] = {
                    "page_load_delay": 1,
                    "click_delay": 0.5,
                    "gamereview_delay": 1,
                    "element_wait_timeout": 5
                }
            
            scraper_config['SPEED_PROFILE'] = speed_profile
            
            return scraper_config
            
        except Exception as e:
            logger.error(f"Error converting config: {e}")
            raise ValueError(f"Invalid configuration: {e}")
    
    def _initialize_components(self):
        """Initialize scraper and parser components"""
        try:
            # Import here to avoid circular imports
            from bga_tm_scraper.scraper import TMScraper
            from bga_tm_scraper.parser import Parser
            
            # Initialize scraper with config dict
            self.scraper = TMScraper(
                chromedriver_path=self.scraper_config.get('CHROMEDRIVER_PATH'),
                chrome_path=self.scraper_config.get('CHROME_PATH'),
                request_delay=self.scraper_config.get('REQUEST_DELAY', 1),
                headless=True,  # Always headless for GUI
                email=self.scraper_config.get('BGA_EMAIL'),
                password=self.scraper_config.get('BGA_PASSWORD')
            )
            
            # Override speed settings if available
            if 'CURRENT_SPEED' in self.scraper_config:
                self.scraper.speed_settings = self.scraper_config['CURRENT_SPEED']
                self.scraper.speed_profile = self.scraper_config['SPEED_PROFILE']
            
            # Initialize parser
            self.parser = Parser()
            
            logger.info("Scraper components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing scraper components: {e}")
            raise RuntimeError(f"Failed to initialize scraper: {e}")
    
    def start_browser_and_login(self) -> bool:
        """
        Start browser and login
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.scraper:
                raise RuntimeError("Scraper not initialized")
            
            success = self.scraper.start_browser_and_login()
            if success:
                logger.info("Browser started and login successful")
            else:
                logger.error("Browser start or login failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error starting browser and login: {e}")
            return False
    
    def scrape_player_game_history(self, player_id: str, max_clicks: int = 1000, stop_event: Optional[threading.Event] = None) -> List[Dict]:
        """
        Scrape player's game history
        
        Args:
            player_id: Player ID to scrape
            max_clicks: Maximum clicks on "See more"
            stop_event: Optional threading event to signal stopping
            
        Returns:
            list: List of game data dictionaries
        """
        try:
            if not self.scraper:
                raise RuntimeError("Scraper not initialized")
            
            if self.progress_callback:
                self.progress_callback(f"🔍 Scraping player {player_id} game history...")
            
            games_data = self.scraper.scrape_player_game_history(
                player_id,
                max_clicks,
                progress_callback=self.progress_callback,
                stop_event=stop_event
            )
            
            logger.info(f"Scraped {len(games_data)} games for player {player_id}")
            return games_data
            
        except Exception as e:
            logger.error(f"Error scraping player game history for {player_id}: {e}")
            return []
    
    def scrape_table_only_memory(self, table_id: str, player_id: str) -> Optional[Dict]:
        """
        Scrape table page only, keeping data in memory
        
        Args:
            table_id: Table ID to scrape
            player_id: Player ID for perspective
            
        Returns:
            dict: Scraped table data or None if failed
        """
        try:
            if not self.scraper:
                raise RuntimeError("Scraper not initialized")
            
            # Scrape table without saving raw HTML
            result = self.scraper.scrape_table_only(table_id, player_id, save_raw=False, raw_data_dir=None)
            
            if result and result.get('success'):
                logger.info(f"Successfully scraped table {table_id} in memory")
                return result
            else:
                logger.warning(f"Failed to scrape table {table_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping table {table_id} in memory: {e}")
            return None
    
    def scrape_table_and_replay_memory(self, table_id: str, player_id: str) -> Optional[Dict]:
        """
        Scrape table and replay pages, keeping data in memory and parsing immediately
        
        Args:
            table_id: Table ID to scrape
            player_id: Player ID for perspective
            
        Returns:
            dict: Parsed game data ready for API upload, or None if failed
            Special case: Returns {'daily_limit_reached': True} if daily limit is hit
        """
        try:
            if not self.scraper or not self.parser:
                raise RuntimeError("Scraper or parser not initialized")
            
            logger.info(f"Starting scrape_table_and_replay for game {table_id}")
            
            # Scrape table and replay without saving raw HTML
            result = self.scraper.scrape_table_and_replay(table_id, player_id, save_raw=True, raw_data_dir=None)
            
            logger.info(f"Scraper returned result for {table_id}: {type(result)}")
            if result:
                logger.info(f"Result keys: {list(result.keys())}")
                logger.info(f"Success: {result.get('success')}")
                logger.info(f"Limit reached: {result.get('limit_reached')}")
                
                # Check replay_data for limit_reached flag
                replay_data = result.get('replay_data', {})
                if replay_data:
                    logger.info(f"Replay data keys: {list(replay_data.keys())}")
                    logger.info(f"Replay limit reached: {replay_data.get('limit_reached')}")
            
            if not result:
                logger.warning(f"Failed to scrape table and replay for {table_id}")
                return None
            
            # Check for daily limit reached in main result
            if result.get('limit_reached'):
                logger.warning(f"Daily replay limit reached when processing game {table_id} (main result)")
                if not self.config_manager.get_replay_limit_hit_at():
                    self.config_manager.set_replay_limit_hit_at(datetime.now().isoformat())
                return {'daily_limit_reached': True}

            # Check for daily limit reached in replay_data
            replay_data = result.get('replay_data', {})
            if replay_data and replay_data.get('limit_reached'):
                logger.warning(f"Daily replay limit reached when processing game {table_id} (replay data)")
                if not self.config_manager.get_replay_limit_hit_at():
                    self.config_manager.set_replay_limit_hit_at(datetime.now().isoformat())
                return {'daily_limit_reached': True}

            # Check for error indicating daily limit
            if replay_data and replay_data.get('error') == 'replay_limit_reached':
                logger.warning(f"Daily replay limit reached when processing game {table_id} (error flag)")
                if not self.config_manager.get_replay_limit_hit_at():
                    self.config_manager.set_replay_limit_hit_at(datetime.now().isoformat())
                return {'daily_limit_reached': True}

            if not result.get('success'):
                logger.warning(f"Failed to scrape table and replay for {table_id}")
                return None

            # On successful scrape, clear the limit timestamp
            self.config_manager.set_replay_limit_hit_at(None)
            
            # Extract HTML content from result
            table_html = result.get('table_data', {}).get('html_content', '')
            replay_html = replay_data.get('html_content', '')
            
            if not table_html:
                logger.error(f"No table HTML found for {table_id}")
                return None
            
            if not replay_html:
                logger.error(f"No replay HTML found for {table_id}")
                return None
            
            # Parse the game data in memory using new unified method
            # First parse table metadata
            game_metadata = self.parser.parse_table_metadata(table_html)
            
            # Use unified parsing method
            game_data = self.parser.parse_complete_game(
                replay_html=replay_html,
                game_metadata=game_metadata,
                table_id=table_id,
                player_perspective=player_id
            )
            
            if game_data:
                # Convert GameData object to dictionary format for GUI
                result = self.parser._convert_game_data_to_api_format(game_data, table_id, player_id)
                logger.info(f"Successfully parsed game {table_id} in memory")
                return result
            else:
                logger.error(f"Failed to parse game {table_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping and parsing game {table_id} in memory: {e}")
            return None

    def scrape_replay_only_with_assignment_metadata(self, table_id: str, version_id: str, player_perspective: str, assignment_metadata: Dict[str, Any], version: Optional[str] = None) -> Optional[Dict]:
        """
        Scrape only replay page using assignment metadata (optimized for replay scraping assignments)
        
        Args:
            table_id: Table ID to scrape
            version_id: Version ID from assignment
            player_perspective: Player ID for perspective
            assignment_metadata: Assignment data containing ELO info, player data, etc.
            version: Optional GUI version string
            
        Returns:
            dict: Parsed game data ready for API upload, or None if failed
            Special case: Returns {'daily_limit_reached': True} if daily limit is hit
        """
        try:
            if not self.scraper or not self.parser:
                raise RuntimeError("Scraper or parser not initialized")
            
            logger.info(f"Starting replay-only scraping for game {table_id} with assignment metadata")
            
            # Scrape only the replay page using the new method
            replay_result = self.scraper.scrape_replay_only_with_metadata(
                table_id=table_id,
                version_id=version_id,
                player_perspective=player_perspective,
                save_raw=False,
                raw_data_dir=None
            )
            
            if not replay_result:
                logger.warning(f"Failed to scrape replay for {table_id}")
                return None
            
            # Check for daily limit reached
            if replay_result.get('limit_reached'):
                logger.warning(f"Daily replay limit reached when processing game {table_id}")
                if not self.config_manager.get_replay_limit_hit_at():
                    self.config_manager.set_replay_limit_hit_at(datetime.now().isoformat())
                return {'daily_limit_reached': True}

            # Check for error indicating daily limit
            if replay_result.get('error') == 'replay_limit_reached':
                logger.warning(f"Daily replay limit reached when processing game {table_id} (error flag)")
                if not self.config_manager.get_replay_limit_hit_at():
                    self.config_manager.set_replay_limit_hit_at(datetime.now().isoformat())
                return {'daily_limit_reached': True}

            # On successful scrape, clear the limit timestamp
            self.config_manager.set_replay_limit_hit_at(None)
            
            # Extract replay HTML
            replay_html = replay_result.get('html_content', '')
            if not replay_html:
                logger.error(f"No replay HTML found for {table_id}")
                return None
            
            # Convert assignment metadata to GameMetadata format
            game_metadata = self.parser.convert_assignment_to_game_metadata(assignment_metadata)
            
            # Parse the game data using unified method
            game_data = self.parser.parse_complete_game(
                replay_html=replay_html,
                game_metadata=game_metadata,
                table_id=table_id,
                player_perspective=player_perspective
            )
            
            if game_data:
                # Convert GameData object to dictionary format for GUI
                result = self.parser._convert_game_data_to_api_format(game_data, table_id, player_perspective)
                if version and result.get("metadata"):
                    result["metadata"]["scraper_version"] = version
                logger.info(f"Successfully parsed replay-only game {table_id} with assignment metadata")
                return result
            else:
                logger.error(f"Failed to parse replay-only game {table_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error in replay-only scraping with assignment metadata for {table_id}: {e}")
            return None
    
    def close_browser(self):
        """Close the browser"""
        try:
            if self.scraper:
                self.scraper.close_browser()
                logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    def refresh_authentication(self) -> bool:
        """
        Refresh authentication if session expires
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.scraper:
                return False
            
            success = self.scraper.refresh_authentication()
            if success:
                logger.info("Authentication refreshed successfully")
            else:
                logger.warning("Authentication refresh failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error refreshing authentication: {e}")
            return False


def create_scraper_from_gui_config(config_manager, progress_callback: Optional[Callable] = None) -> InMemoryScraper:
    """
    Create an InMemoryScraper instance from GUI config manager
    
    Args:
        config_manager: GUI config manager instance
        progress_callback: Optional callback for progress updates
        
    Returns:
        InMemoryScraper: Configured scraper instance
    """
    try:
        # Get BGA credentials using the proper decoding method
        email, password, _ = config_manager.get_bga_credentials()
        
        # Get all config values
        config_dict = {
            'bga_credentials': {
                'email': email,
                'password': password  # Now using decoded password
            },
            'chrome_settings': {
                'chrome_path': config_manager.get_value('browser_settings', 'chrome_path'),
                'chromedriver_path': config_manager.get_value('browser_settings', 'chromedriver_path')
            },
            'api_settings': {
                'api_key': config_manager.get_value('api_settings', 'api_key')
            },
            'scraping_settings': {
                'speed_profile': config_manager.get_value('scraping_settings', 'speed_profile'),
                'request_delay': config_manager.get_value('scraping_settings', 'request_delay')
            }
        }
        
        return InMemoryScraper(config_manager, config_dict, progress_callback)
        
    except Exception as e:
        logger.error(f"Error creating scraper from GUI config: {e}")
        raise RuntimeError(f"Failed to create scraper: {e}")
