"""
Web scraper for Terraforming Mars replay data from BoardGameArena
"""
import time
import os
import logging
import re
import requests
from typing import List, Optional, Dict, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from .bga_session import BGASession

logger = logging.getLogger(__name__)

import config
from config import TERRAFORMING_MARS_GAME_ID

class TMScraper:
    """Web scraper for Terraforming Mars replays from BoardGameArena"""
    
    def __init__(self, chromedriver_path: str, chrome_path: str=None, request_delay: int = 1, headless: bool = False,
                 email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the scraper
        
        Args:
            chromedriver_path: Path to ChromeDriver executable
            request_delay: Delay between requests in seconds
            headless: Whether to run Chrome in headless mode
            email: BGA account email (optional, will try to load from config if not provided)
            password: BGA account password (optional, will try to load from config if not provided)
        """
        self.chromedriver_path = chromedriver_path
        self.chrome_path = chrome_path
        self.request_delay = request_delay
        self.headless = headless
        self.driver = None
        
        # Authentication credentials
        self.email = email
        self.password = password
        
        # Try to load credentials from config if not provided
        if not self.email or not self.password:
            try:
                from config import BGA_EMAIL, BGA_PASSWORD
                self.email = self.email or BGA_EMAIL
                self.password = self.password or BGA_PASSWORD
            except ImportError:
                logger.warning("No credentials provided and could not load from config")
        
        # Session manager
        self.session: Optional[BGASession] = None
        
        # Session for direct HTTP requests
        self.requests_session: Optional[requests.Session] = None
        
        # Load speed settings from config
        try:
            from config import CURRENT_SPEED, SPEED_PROFILE
            self.speed_settings = CURRENT_SPEED
            self.speed_profile = SPEED_PROFILE
            logger.info(f"Using speed profile: {SPEED_PROFILE}")
            logger.info(f"Speed settings: {CURRENT_SPEED}")
        except ImportError:
            # Fallback to default settings if config not available
            self.speed_settings = {
                "page_load_delay": 1,
                "click_delay": 0.3,
                "gamereview_delay": 1,
                "element_wait_timeout": 5
            }
            self.speed_profile = "DEFAULT"
            logger.warning("Could not load speed settings from config, using defaults")
    
    def start_browser_and_login(self) -> bool:
        """
        Start browser and perform automated login using session manager
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.email or not self.password:
            logger.error("Email and password are required for automated login")
            print("❌ Email and password are required for automated login")
            print("Please provide credentials via constructor or config.py")
            return False
        
        try:
            # Initialize session manager
            print("🔐 Starting automated login process...")
            self.session = BGASession(
                email=self.email,
                password=self.password,
                chromedriver_path=self.chromedriver_path,
                chrome_path=self.chrome_path,
                headless=self.headless
            )
            
            # Perform authentication
            if not self.session.login():
                logger.error("Authentication failed")
                print("❌ Automated login failed")
                return False
            
            # Get the authenticated browser driver
            self.driver = self.session.get_driver()
            
            print("✅ Automated login completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error during automated login: {e}")
            print(f"❌ Error during automated login: {e}")
            return False

    def start_browser(self):
        """Start the Chrome browser (legacy method - use start_browser_and_login for automated login)"""
        print("Starting Chrome browser...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Add useful Chrome options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        if self.chrome_path:
            # If a custom Chrome path is provided, set it
            options.binary_location = self.chrome_path

        # Set user agent to avoid detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(self.chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✅ Chrome browser started successfully!")
        return self.driver
    
    def login_to_bga(self):
        """Navigate to BGA and wait for user to log in manually"""
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        print("Navigating to BoardGameArena...")
        self.driver.get("https://boardgamearena.com")
        
        print("\n" + "="*60)
        print("🔐 MANUAL LOGIN REQUIRED")
        print("Please log into BoardGameArena in the browser window that opened.")
        print("After logging in, come back here and press Enter to continue...")
        print("="*60)
        
        input("Press Enter when you're logged in and ready to continue...")
        
        # Verify login by checking for logout link or user menu
        try:
            # Look for common elements that indicate login
            WebDriverWait(self.driver, 10).until(
                lambda driver: 'logout' in driver.page_source.lower() or 
                              'my account' in driver.page_source.lower() or
                              'player_name' in driver.page_source.lower()
            )
            print("✅ Login verified!")
            return True
        except:
            print("⚠️  Could not verify login, but continuing anyway...")
            return True
    
    def scrape_table_only(self, table_id: str, player_perspective: str, save_raw: bool = True, raw_data_dir: str = None) -> Optional[Dict]:
        """
        Scrape only the table page for a game, extract player info and check Arena mode
        
        Args:
            table_id: BGA table ID
            player_perspective: Player ID whose perspective this table is being scraped from
            save_raw: Whether to save raw HTML
            raw_data_dir: Directory to save raw HTML files
            
        Returns:
            dict: Table data with player info and Arena mode status, or None if failed
        """
        if raw_data_dir is None:
            raw_data_dir = config.RAW_DATA_DIR
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        logger.info(f"Scraping table only for game {table_id}")
        
        try:
            # Step 1: Scrape table page for ELO data
            logger.info("Scraping table page...")
            table_data = self.scrape_table_page(table_id, player_perspective, save_raw, raw_data_dir)
            if not table_data:
                logger.error(f"Failed to scrape table page for {table_id}")
                return None

            # Step 2: Extract player information using parser
            logger.info("Extracting player information...")
            from .parser import Parser
            parser = Parser()
            elo_data = parser.parse_elo_data(table_data['html_content'])

            # Step 3: Check game mode
            game_mode = parser.parse_game_mode(table_data['html_content'])
            
            # Step 4: Extract map from table page
            logger.info("Extracting map...")
            map_name = self._extract_map_from_table(table_data['html_content'])
            if map_name:
                logger.info(f"Successfully extracted map: {map_name}")
                print(f"✅ Map extracted: {map_name}")
            else:
                logger.debug("Could not extract map")
                print("⚠️  Could not extract map")
            
            # Step 5: Extract Corporate Era setting from table page
            logger.info("Extracting Corporate Era setting...")
            corporate_era_on = self._extract_corporate_era_from_table(table_data['html_content'])
            if corporate_era_on is not None:
                logger.info(f"Successfully extracted Corporate Era: {corporate_era_on}")
                print(f"✅ Corporate Era extracted: {'On' if corporate_era_on else 'Off'}")
            else:
                logger.debug("Could not extract Corporate Era setting")
                print("⚠️  Could not extract Corporate Era setting")
            
            # Step 6: Extract Prelude setting from table page
            logger.info("Extracting Prelude setting...")
            prelude_on = self._extract_prelude_from_table(table_data['html_content'])
            if prelude_on is not None:
                logger.info(f"Successfully extracted Prelude: {prelude_on}")
                print(f"✅ Prelude extracted: {'On' if prelude_on else 'Off'}")
            else:
                logger.debug("Could not extract Prelude setting")
                print("⚠️  Could not extract Prelude setting")
            
            # Step 7: Extract Draft setting from table page
            logger.info("Extracting Draft setting...")
            draft_on = self._extract_draft_from_table(table_data['html_content'])
            if draft_on is not None:
                logger.info(f"Successfully extracted Draft: {draft_on}")
                print(f"✅ Draft extracted: {'Yes' if draft_on else 'No'}")
            else:
                logger.debug("Could not extract Draft setting")
                print("⚠️  Could not extract Draft setting")
            
            # Step 8: Extract Colonies setting from table page
            logger.info("Extracting Colonies setting...")
            colonies_on = self._extract_colonies_from_table(table_data['html_content'])
            if colonies_on is not None:
                logger.info(f"Successfully extracted Colonies: {colonies_on}")
                print(f"✅ Colonies extracted: {'On' if colonies_on else 'Off'}")
            else:
                logger.debug("Could not extract Colonies setting")
                print("⚠️  Could not extract Colonies setting")
            
            # Step 9: Extract Beginners Corporations setting from table page
            logger.info("Extracting Beginners Corporations setting...")
            beginners_corporations_on = self._extract_beginners_corporations_from_table(table_data['html_content'])
            if beginners_corporations_on is not None:
                logger.info(f"Successfully extracted Beginners Corporations: {beginners_corporations_on}")
                print(f"✅ Beginners Corporations extracted: {'Yes' if beginners_corporations_on else 'No'}")
            else:
                logger.debug("Could not extract Beginners Corporations setting")
                print("⚠️  Could not extract Beginners Corporations setting")
            
            # Step 10: Extract Game Speed setting from table page
            logger.info("Extracting Game Speed setting...")
            game_speed = self._extract_game_speed_from_table(table_data['html_content'])
            if game_speed:
                logger.info(f"Successfully extracted Game Speed: {game_speed}")
                print(f"✅ Game Speed extracted: {game_speed}")
            else:
                logger.debug("Could not extract Game Speed setting")
                print("⚠️  Could not extract Game Speed setting")
            
            # Extract player IDs from ELO data (they're already included now)
            player_ids = []
            if elo_data:
                player_ids = [elo.player_id for elo in elo_data.values() if elo.player_id]
                logger.info(f"Found {len(player_ids)} player IDs from ELO data: {player_ids}")
            else:
                logger.warning("No ELO data found - cannot extract player IDs")
            
            # Step 11: Extract game date from table page using parser
            logger.info("Extracting game date...")
            from .parser import Parser
            parser = Parser()
            game_date_info = parser._extract_game_date_from_table(table_data['html_content'])
            
            # Step 12: Extract version number from gamereview page
            logger.info("Extracting version number...")
            version = self.extract_version_from_gamereview(table_id)
            if version:
                logger.info(f"Successfully extracted version: {version}")
                print(f"✅ Version extracted: {version}")
            else:
                logger.warning("Could not extract version number")
                print("⚠️  Could not extract version number")

            # Step 13: Combine results
            result_data = {
                'table_id': table_id,
                'table_data': table_data,
                'scraped_at': datetime.now().isoformat(),
                'success': True,
                'game_mode': game_mode,
                'map': map_name,
                'corporate_era_on': corporate_era_on,
                'prelude_on': prelude_on,
                'draft_on': draft_on,
                'colonies_on': colonies_on,
                'beginners_corporations_on': beginners_corporations_on,
                'game_speed': game_speed,
                'player_ids': player_ids,
                'elo_data': elo_data,
                'version': version,
                'game_date_info': game_date_info,  # Include extracted game date
                'table_only': True  # Flag to indicate this was table-only scraping
            }
            
            logger.info(f"Successfully scraped {game_mode} game {table_id} (table only)")
            
            return result_data
            
        except Exception as e:
            logger.error(f"Error scraping table only for {table_id}: {e}")
            return None

    def scrape_table_and_replay(self, table_id: str, player_perspective: str, save_raw: bool = True, raw_data_dir: str = None) -> Optional[Dict]:
        """
        Scrape both table page and replay page for a game
        
        Args:
            table_id: BGA table ID
            player_perspective: Player ID whose perspective this game is being scraped from
            save_raw: Whether to save raw HTML
            raw_data_dir: Directory to save raw HTML files
            
        Returns:
            dict: Combined scraped data or None if failed
        """
        if raw_data_dir is None:
            raw_data_dir = config.RAW_DATA_DIR
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        logger.info(f"Scraping table and replay for game {table_id}")
        
        try:
            # Step 1: Scrape table page for ELO data
            logger.info("Scraping table page...")
            table_data = self.scrape_table_page(table_id, player_perspective, save_raw, raw_data_dir)
            if not table_data:
                logger.error(f"Failed to scrape table page for {table_id}")
                return None

            # Step 2: Determine game mode
            logger.info("Determining game mode...")

            from .parser import Parser
            parser = Parser()
            game_mode = parser.parse_game_mode(table_data['html_content'])
            logger.info(f"Detected game mode: {game_mode}")
            is_arena_mode = game_mode == "Arena mode"

            print(f"✅ Game {table_id} is {game_mode} - proceeding with scraping")

            # Step 3: Extract player IDs from table page
            logger.info("Extracting player IDs...")
            player_ids = self.extract_player_ids_from_table(table_data['html_content'])
            if not player_ids:
                logger.warning(f"No player IDs found in table page for {table_id}")
                
            # Step 4: Extract version number from gamereview page
            logger.info("Extracting version number...")
            version = self.extract_version_from_gamereview(table_id)
            if version:
                logger.info(f"Successfully extracted version: {version}")
                print(f"✅ Version extracted: {version}")
            else:
                logger.warning("Could not extract version number")
                print("⚠️  Could not extract version number")

            # Step 5: Construct and scrape replay page
            logger.info("Extracting replay...")
            replay_data = self.scrape_replay_from_table(table_id, player_ids[0], save_raw, raw_data_dir)
            if not replay_data:
                logger.error(f"Failed to scrape replay page for {table_id}")
                # Continue with just table data
                replay_data = {}
            
            # Step 6: Combine results
            combined_data = {
                'table_id': table_id,
                'table_data': table_data,
                'replay_data': replay_data,
                'scraped_at': datetime.now().isoformat(),
                'success': True,
                'arena_mode': is_arena_mode,
                'version': version
            }
            
            game_mode_text = "Arena" if is_arena_mode else "Normal"
            logger.info(f"Successfully scraped {game_mode_text} mode game {table_id}")
            return combined_data
            
        except Exception as e:
            logger.error(f"Error scraping table and replay for {table_id}: {e}")
            return None
    
    def scrape_table_page(self, table_id: str, player_perspective: str, save_raw: bool = True, raw_data_dir: str = None) -> Optional[Dict]:
        """
        Scrape a table page for ELO information
        
        Args:
            table_id: BGA table ID
            player_perspective: Player ID whose perspective this table is being scraped from
            save_raw: Whether to save raw HTML
            raw_data_dir: Directory to save raw HTML files
            
        Returns:
            dict: Table page data or None if failed
        """
        # Handle memory-only mode
        if raw_data_dir is None and hasattr(config, 'RAW_DATA_DIR'):
            raw_data_dir = config.RAW_DATA_DIR
        
        # Validate player_perspective parameter to prevent os.path.join errors
        if not isinstance(player_perspective, str):
            raise TypeError(f"player_perspective must be a string, got {type(player_perspective).__name__}: {player_perspective}")
        
        # Get table URL template
        if hasattr(config, 'TABLE_URL_TEMPLATE'):
            table_url = config.TABLE_URL_TEMPLATE.format(table_id=table_id)
        else:
            # Fallback for memory-only mode
            table_url = f'https://boardgamearena.com/table?table={table_id}'
        
        logger.info(f"Scraping table page: {table_url}")
        
        try:
            # Navigate to the table URL
            print(f"Navigating to table page: {table_url}")
            self.driver.get(table_url)
            
            # Wait for content to load using smart detection instead of fixed delay
            if not self._wait_for_table_content_to_load(table_id):
                print("❌ Table content failed to load properly")
                return None
            
            # Get the page source after content has loaded
            page_source = self.driver.page_source
            
            # Save raw HTML if requested and raw_data_dir is provided
            if save_raw and raw_data_dir:
                # Create player perspective directory
                player_raw_dir = os.path.join(raw_data_dir, player_perspective)
                os.makedirs(player_raw_dir, exist_ok=True)
                raw_file_path = os.path.join(player_raw_dir, f"table_{table_id}.html")
                
                with open(raw_file_path, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                logger.info(f"Saved table HTML to {raw_file_path}")
            
            # Parse basic table information
            soup = BeautifulSoup(page_source, 'html.parser')
            
            table_data = {
                'table_id': table_id,
                'url': table_url,
                'scraped_at': datetime.now().isoformat(),
                'html_content': page_source,
                'elo_data_found': False
            }
            
            # Look for ELO data
            
            # Check if ELO data is present
            if 'rankdetails' in page_source or 'winpoints' in page_source:
                table_data['elo_data_found'] = True
                logger.info(f"ELO data found in table page for {table_id}")
                print(f"✅ ELO data found in table page")
            else:
                logger.warning(f"No ELO data found in table page for {table_id}")
                print("⚠️  No ELO data found in table page")
            
            logger.info(f"Successfully scraped table page for {table_id}")
            return table_data
            
        except Exception as e:
            logger.error(f"Error scraping table page for {table_id}: {e}")
            print(f"❌ Error scraping table page: {e}")
            return None
    
    def extract_player_ids_from_table(self, html_content: str) -> List[str]:
        """
        Extract player IDs from table page HTML using efficient BeautifulSoup parsing
        
        Args:
            html_content: HTML content of the table page
            
        Returns:
            list: List of player IDs found
        """
        player_ids = []
        
        try:
            logger.info("Parsing HTML with BeautifulSoup...")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Method 1: Look for elements with player IDs in common attributes
            logger.info("Searching for player IDs in element attributes...")
            
            # Look for elements with IDs containing player IDs
            for element in soup.find_all(attrs={'id': True}):
                element_id = element.get('id', '')
                # Look for 8+ digit numbers in IDs
                id_matches = re.findall(r'\d{8,}', element_id)
                for match in id_matches:
                    if match not in player_ids:
                        player_ids.append(match)
            
            # Look for elements with classes containing player IDs
            for element in soup.find_all(attrs={'class': True}):
                classes = element.get('class', [])
                for class_name in classes:
                    class_matches = re.findall(r'\d{8,}', str(class_name))
                    for match in class_matches:
                        if match not in player_ids:
                            player_ids.append(match)
            
            # Method 2: Look for data attributes
            logger.info("Searching for player IDs in data attributes...")
            for element in soup.find_all(attrs=lambda x: any(attr.startswith('data-') for attr in x.keys()) if x and hasattr(x, 'keys') else False):
                try:
                    for attr_name, attr_value in element.attrs.items():
                        if attr_name.startswith('data-'):
                            data_matches = re.findall(r'\d{8,}', str(attr_value))
                            for match in data_matches:
                                if match not in player_ids:
                                    player_ids.append(match)
                except (AttributeError, TypeError) as e:
                    logger.debug(f"Skipping element due to attribute error: {e}")
                    continue
            
            # Method 3: Look in href attributes (links to player profiles)
            logger.info("Searching for player IDs in links...")
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'player' in href.lower():
                    href_matches = re.findall(r'\d{8,}', href)
                    for match in href_matches:
                        if match not in player_ids:
                            player_ids.append(match)
            
            # Method 4: Fallback - limited regex search on smaller chunks
            if not player_ids:
                logger.info("Fallback: searching in text content around player names...")
                player_name_elements = soup.find_all('span', class_='playername')
                for elem in player_name_elements:
                    # Get parent elements and search in a limited scope
                    parent = elem.parent
                    if parent:
                        parent_text = str(parent)[:1000]  # Limit to 1000 chars to avoid backtracking
                        simple_matches = re.findall(r'\b\d{8,}\b', parent_text)
                        for match in simple_matches:
                            if match not in player_ids:
                                player_ids.append(match)
            
            # Remove duplicates while preserving order and filter valid IDs
            unique_player_ids = []
            for pid in player_ids:
                if len(pid) >= 8 and len(pid) <= 12 and pid not in unique_player_ids:  # Reasonable length for player IDs
                    unique_player_ids.append(pid)
            
            logger.info(f"Extracted {len(unique_player_ids)} player IDs from table page: {unique_player_ids}")
            return unique_player_ids
            
        except Exception as e:
            logger.error(f"Error extracting player IDs: {e}")
            return []
    
    def extract_version_from_gamereview(self, table_id: str) -> Optional[str]:
        """
        Extract the version number from the gamereview page using multiple robust patterns
        
        Args:
            table_id: BGA table ID
            
        Returns:
            str: Version number (e.g., "250505-1448") or None if not found
        """
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        gamereview_url = f"https://boardgamearena.com/gamereview?table={table_id}"
        logger.info(f"Extracting version from gamereview page: {gamereview_url}")
        
        try:
            # Navigate to the gamereview page
            print(f"Navigating to gamereview page: {gamereview_url}")
            self.driver.get(gamereview_url)
            
            # Wait for JavaScript content to load instead of just using a fixed delay
            if not self._wait_for_gamereview_content_to_load(table_id):
                print("❌ Gamereview content failed to load properly")
                return None
            
            # Get the page source after content has loaded
            page_source = self.driver.page_source
            
            # Log basic page characteristics for debugging
            logger.info(f"Content loaded successfully - HTML length: {len(page_source)} chars")
            
            # Try multiple extraction patterns in order of reliability
            version = self._extract_version_with_multiple_patterns(page_source, table_id)
            
            if version:
                logger.info(f"Successfully extracted version: {version}")
                print(f"✅ Found version number: {version}")
                return version
            else:
                logger.warning(f"No version number found in gamereview page for table {table_id}")
                print("⚠️  No version number found in gamereview page")
                
                # Save HTML and debug info when extraction fails
                self._save_debug_info_for_failed_extraction(table_id, page_source, gamereview_url)
                return None
            
        except Exception as e:
            logger.error(f"Error extracting version from gamereview for {table_id}: {e}")
            print(f"❌ Error extracting version: {e}")
            return None

    def _extract_version_with_multiple_patterns(self, html_content: str, table_id: str) -> Optional[str]:
        """
        Extract version number using only the most reliable pattern (replay URLs)
        
        Args:
            html_content: HTML content of the gamereview page
            table_id: Table ID for logging purposes
            
        Returns:
            str: Version number if found, None otherwise
        """
        logger.debug(f"Extracting version from replay URLs for table {table_id}")
        
        # Use only the most reliable pattern: Direct replay links
        # This pattern has proven to be the most accurate in testing
        replay_pattern = r'/archive/replay/(\d{6}-\d{4})/'
        
        try:
            matches = re.findall(replay_pattern, html_content, re.IGNORECASE)
            logger.info(f"Replay URL pattern search: found {len(matches)} matches")
            
            if matches:
                # Remove duplicates and get the first unique match
                unique_matches = list(dict.fromkeys(matches))  # Preserves order
                version = unique_matches[0]
                
                logger.info(f"Version found using replay URL pattern: {version}")
                logger.debug(f"Replay URL pattern found {len(matches)} total matches, using first unique: {version}")
                
                # Validate the version format (6 digits, dash, 4 digits)
                if re.match(r'^\d{6}-\d{4}$', version):
                    return version
                else:
                    logger.warning(f"Invalid version format from replay URL: {version}")
                    return None
            else:
                # Log some context about what we're searching in
                logger.info(f"No replay URL matches found. HTML contains 'archive': {'archive' in html_content.lower()}")
                logger.info(f"HTML contains 'replay': {'replay' in html_content.lower()}")
                
                # Look for any archive/replay patterns for debugging
                archive_patterns = re.findall(r'/archive/[^/]+/[^/\s"\'<>]+', html_content, re.IGNORECASE)
                if archive_patterns:
                    logger.info(f"Found {len(archive_patterns)} archive patterns (not matching version format): {archive_patterns[:5]}")
                else:
                    logger.info("No archive patterns found at all")
                    
        except Exception as e:
            logger.error(f"Error with replay URL pattern: {e}")
        
        logger.debug(f"No version number found in replay URLs for table {table_id}")
        return None

    def _save_debug_info_for_failed_extraction(self, table_id: str, html_content: str, gamereview_url: str):
        """
        Save HTML content and debug information when version extraction fails
        
        Args:
            table_id: BGA table ID
            html_content: HTML content of the gamereview page
            gamereview_url: URL of the gamereview page
        """
        try:
            import json
            
            # Create timestamp for unique filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save HTML content
            html_filename = f"gamereview_{table_id}_{timestamp}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Create debug information
            debug_info = {
                'table_id': table_id,
                'timestamp': timestamp,
                'gamereview_url': gamereview_url,
                'html_filename': html_filename,
                'page_characteristics': self._analyze_page_characteristics(html_content),
                'pattern_analysis': self._analyze_version_patterns(html_content),
                'extraction_context': {
                    'speed_profile': self.speed_profile,
                    'speed_settings': self.speed_settings,
                    'headless_mode': self.headless
                }
            }
            
            # Save debug JSON
            json_filename = f"version_debug_results_{table_id}_{timestamp}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Debug info saved: {html_filename} and {json_filename}")
            print(f"🔍 Debug files saved: {html_filename} and {json_filename}")
            
        except Exception as e:
            logger.error(f"Error saving debug info: {e}")
            print(f"❌ Error saving debug info: {e}")

    def _analyze_page_characteristics(self, html_content: str) -> Dict:
        """
        Analyze basic characteristics of the HTML page
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            dict: Analysis results
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title found"
            
            # Check for key elements
            characteristics = {
                'title': title_text,
                'has_archive_links': 'archive' in html_content.lower(),
                'has_replay_links': 'replay' in html_content.lower(),
                'has_table_references': f'table' in html_content.lower(),
                'has_version_patterns': bool(re.search(r'\d{6}-\d{4}', html_content)),
                'script_tags_count': len(soup.find_all('script')),
                'div_count': len(soup.find_all('div')),
                'link_count': len(soup.find_all('a')),
                'contains_error_messages': any(error in html_content.lower() for error in ['error', 'fatal', 'must be logged']),
                'page_seems_loaded': len(html_content) > 10000  # Rough heuristic
            }
            
            return characteristics
            
        except Exception as e:
            logger.error(f"Error analyzing page characteristics: {e}")
            return {'error': str(e)}

    def _analyze_version_patterns(self, html_content: str) -> Dict:
        """
        Analyze version-related patterns in the HTML content
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            dict: Pattern analysis results
        """
        try:
            analysis = {}
            
            # Primary pattern: replay URLs
            replay_pattern = r'/archive/replay/(\d{6}-\d{4})/'
            replay_matches = re.findall(replay_pattern, html_content, re.IGNORECASE)
            analysis['replay_url_pattern'] = {
                'pattern': replay_pattern,
                'matches_count': len(replay_matches),
                'matches': replay_matches[:10],  # First 10 matches
                'unique_matches': list(dict.fromkeys(replay_matches))[:10]
            }
            
            # Look for any 6-4 digit patterns
            version_pattern = r'\b(\d{6}-\d{4})\b'
            version_matches = re.findall(version_pattern, html_content)
            analysis['general_version_pattern'] = {
                'pattern': version_pattern,
                'matches_count': len(version_matches),
                'matches': version_matches[:10],
                'unique_matches': list(dict.fromkeys(version_matches))[:10]
            }
            
            # Look for archive patterns (broader)
            archive_pattern = r'/archive/[^/\s"\'<>]+'
            archive_matches = re.findall(archive_pattern, html_content, re.IGNORECASE)
            analysis['archive_pattern'] = {
                'pattern': archive_pattern,
                'matches_count': len(archive_matches),
                'matches': archive_matches[:10],
                'unique_matches': list(dict.fromkeys(archive_matches))[:10]
            }
            
            # Sample content around potential matches
            if replay_matches:
                # Find context around the first replay match
                first_match = replay_matches[0]
                match_index = html_content.find(f'/archive/replay/{first_match}/')
                if match_index != -1:
                    start = max(0, match_index - 200)
                    end = min(len(html_content), match_index + 200)
                    analysis['first_match_context'] = html_content[start:end]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing version patterns: {e}")
            return {'error': str(e)}

    def _wait_for_table_content_to_load(self, table_id: str) -> bool:
        """
        Wait for the table page content to load properly instead of using fixed delays
        
        Args:
            table_id: BGA table ID for logging purposes
            
        Returns:
            bool: True if content loaded successfully, False if timeout or error
        """
        try:
            # Get timeout from speed settings
            timeout = self.speed_settings.get('element_wait_timeout', 10)
            
            print(f"⏱️  Waiting for table content to load (timeout: {timeout}s)")
            logger.info(f"Waiting for table content to load for table {table_id}")
            
            # Strategy 1: Wait for specific content indicators to appear
            wait = WebDriverWait(self.driver, timeout)
            
            # Try multiple strategies to detect when content is loaded
            content_loaded = False
            
            # Strategy 1: Wait for ELO data elements with actual populated content
            try:
                logger.info("Strategy 1: Waiting for populated ELO data elements...")
                
                def elo_data_populated(driver):
                    try:
                        # Look for elements that contain actual ELO numbers, not just empty containers
                        elo_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Arena points:') or contains(text(), 'Game rank:') or contains(text(), 'Arena points ') or contains(text(), 'Game rank ')]")
                        
                        # Check if we found elements with actual numerical data
                        for element in elo_elements:
                            text = element.text.strip()
                            # Look for patterns like "Arena points: 1234" or "Game rank: 567"
                            if re.search(r'(Arena points|Game rank)[:]\s*[-+]?\d+', text):
                                logger.info(f"Found populated ELO data: {text[:50]}")
                                return True
                        
                        # Alternative: look for score entries with actual numbers
                        score_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='rankdetails'], [class*='winpoints']")
                        for element in score_elements:
                            text = element.text.strip()
                            # Check if the element contains actual numbers (not just empty)
                            if re.search(r'\d+', text) and len(text) > 5:  # Must have numbers and substantial content
                                logger.info(f"Found populated score element: {text[:50]}")
                                return True
                        
                        return False
                    except:
                        return False
                
                wait.until(elo_data_populated)
                logger.info("Populated ELO data elements found - content appears to be loaded")
                print("✅ Populated ELO data detected - content loaded")
                content_loaded = True
            except:
                logger.info("Strategy 1 failed: No populated ELO data elements found")
            
            # Strategy 2: Wait for player name elements
            if not content_loaded:
                try:
                    logger.info("Strategy 2: Waiting for player name elements...")
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.playername")))
                    
                    # Verify we have multiple players (typical game has 2-5 players)
                    player_elements = self.driver.find_elements(By.CSS_SELECTOR, "span.playername")
                    if len(player_elements) >= 2:
                        logger.info(f"Found {len(player_elements)} player names - content appears loaded")
                        print(f"✅ Player names detected ({len(player_elements)} players) - content loaded")
                        content_loaded = True
                    else:
                        logger.info(f"Only found {len(player_elements)} player names - waiting for more")
                except:
                    logger.info("Strategy 2 failed: No player name elements found")
            
            # Strategy 3: Wait for game status/completion elements
            if not content_loaded:
                try:
                    logger.info("Strategy 3: Waiting for game status elements...")
                    wait.until(EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".game_result, .game_status")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Finished') or contains(text(), 'Winner')]"))
                    ))
                    logger.info("Game status elements found")
                    print("✅ Game status detected - content loaded")
                    content_loaded = True
                except:
                    logger.info("Strategy 3 failed: No game status elements found")
            
            # Strategy 4: Wait for overall-content div to be populated with table-specific content
            if not content_loaded:
                try:
                    logger.info("Strategy 4: Waiting for overall-content to be populated...")
                    
                    def table_content_populated(driver):
                        try:
                            overall_content = driver.find_element(By.ID, "overall-content")
                            content_text = overall_content.text.strip()
                            inner_html = overall_content.get_attribute('innerHTML').strip()
                            
                            # Content is considered loaded if:
                            # 1. It has substantial text content, AND
                            # 2. It contains table-specific indicators
                            has_text = len(content_text) > 200
                            has_table_content = any(indicator in inner_html.lower() for indicator in [
                                'playername', 'rankdetails', 'winpoints', 'arena points', 'game rank'
                            ])
                            
                            if has_text and has_table_content:
                                logger.info(f"Table content populated: text={len(content_text)} chars, has_table_content={has_table_content}")
                                return True
                            return False
                        except:
                            return False
                    
                    wait.until(table_content_populated)
                    logger.info("Overall-content div populated with table content")
                    print("✅ Table content populated - content loaded")
                    content_loaded = True
                except:
                    logger.info("Strategy 4 failed: Overall-content not populated with table content")
            
            # Strategy 5: Progressive delay with content validation (fallback)
            if not content_loaded:
                logger.info("Strategy 5: Using progressive delays with content validation...")
                delays = [0.5, 1.0, 2.0]  # Shorter delays for table pages
                
                for delay in delays:
                    print(f"⏱️  Waiting {delay}s for content to load...")
                    time.sleep(delay)
                    
                    # Check if content has appeared
                    page_source = self.driver.page_source
                    
                    # Look for ELO/ranking data in the page source
                    if any(indicator in page_source.lower() for indicator in [
                        'rankdetails', 'winpoints', 'arena points', 'game rank'
                    ]):
                        logger.info(f"Content loaded after {delay}s delay - ELO data found")
                        print(f"✅ Content loaded after {delay}s - ELO data detected")
                        content_loaded = True
                        break
                    
                    # Look for player names
                    try:
                        soup = BeautifulSoup(page_source, 'html.parser')
                        player_names = soup.find_all('span', class_='playername')
                        if len(player_names) >= 2:
                            logger.info(f"Content loaded after {delay}s delay - {len(player_names)} player names found")
                            print(f"✅ Content loaded after {delay}s - player names detected")
                            content_loaded = True
                            break
                    except:
                        pass
                    
                    logger.info(f"Content not ready after {delay}s, trying next delay...")
            
            if content_loaded:
                # Give a small additional delay to ensure everything is fully rendered
                time.sleep(0.2)  # Shorter final delay for table pages
                logger.info("Table content loading completed successfully")
                return True
            else:
                logger.warning(f"Table content failed to load within timeout for table {table_id}")
                print("⚠️  Table content loading timeout - proceeding anyway")
                
                # Even if we timeout, let's try to proceed - sometimes content is there but not detected
                return True
                
        except Exception as e:
            logger.error(f"Error waiting for table content to load: {e}")
            print(f"❌ Error waiting for table content: {e}")
            # Don't fail completely - try to proceed
            return True

    def _wait_for_player_history_content_to_load(self, player_id: str) -> bool:
        """
        Wait for the player history page content to load properly instead of using fixed delays
        
        Args:
            player_id: BGA player ID for logging purposes
            
        Returns:
            bool: True if content loaded successfully, False if timeout or error
        """
        try:
            # Get timeout from speed settings
            timeout = self.speed_settings.get('element_wait_timeout', 10)
            
            print(f"⏱️  Waiting for player history content to load (timeout: {timeout}s)")
            logger.info(f"Waiting for player history content to load for player {player_id}")
            
            # Strategy 1: Wait for specific content indicators to appear
            wait = WebDriverWait(self.driver, timeout)
            
            # Try multiple strategies to detect when content is loaded
            content_loaded = False
            
            # Strategy 1: Wait for game history table or rows to appear
            try:
                logger.info("Strategy 1: Waiting for game history elements...")
                wait.until(EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.gamehistory")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.gamehistory")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tr.gamehistory_row"))
                ))
                logger.info("Game history elements found - content appears to be loaded")
                print("✅ Game history table detected - content loaded")
                content_loaded = True
            except:
                logger.info("Strategy 1 failed: No game history elements found")
            
            # Strategy 2: Wait for "See more" button or game entries
            if not content_loaded:
                try:
                    logger.info("Strategy 2: Waiting for game entries or See more button...")
                    wait.until(EC.any_of(
                        EC.presence_of_element_located((By.ID, "see_more_tables")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.row")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '#')]"))
                    ))
                    logger.info("Game entries or See more button found")
                    print("✅ Game entries detected - content loaded")
                    content_loaded = True
                except:
                    logger.info("Strategy 2 failed: No game entries or See more button found")
            
            # Strategy 3: Wait for table IDs to appear (games with # prefix)
            if not content_loaded:
                try:
                    logger.info("Strategy 3: Waiting for table IDs to appear...")
                    
                    def table_ids_present(driver):
                        try:
                            page_source = driver.page_source
                            # Look for table ID patterns like #12345678
                            table_id_matches = re.findall(r'#\d{8,}', page_source)
                            if len(table_id_matches) >= 1:  # At least one game
                                logger.info(f"Found {len(table_id_matches)} table IDs")
                                return True
                            return False
                        except:
                            return False
                    
                    wait.until(table_ids_present)
                    logger.info("Table IDs found in page content")
                    print("✅ Table IDs detected - content loaded")
                    content_loaded = True
                except:
                    logger.info("Strategy 3 failed: No table IDs found")
            
            # Strategy 4: Progressive delay with content validation (fallback)
            if not content_loaded:
                logger.info("Strategy 4: Using progressive delays with content validation...")
                delays = [1.0, 2.0, 3.0]  # Progressive delays for player history
                
                for delay in delays:
                    print(f"⏱️  Waiting {delay}s for content to load...")
                    time.sleep(delay)
                    
                    # Check if content has appeared
                    page_source = self.driver.page_source
                    
                    # Look for game history indicators
                    if any(indicator in page_source.lower() for indicator in [
                        'gamehistory', 'see_more_tables', 'table_id'
                    ]):
                        logger.info(f"Content loaded after {delay}s delay - game history indicators found")
                        print(f"✅ Content loaded after {delay}s - game history detected")
                        content_loaded = True
                        break
                    
                    # Look for table IDs
                    table_id_matches = re.findall(r'#\d{8,}', page_source)
                    if len(table_id_matches) >= 1:
                        logger.info(f"Content loaded after {delay}s delay - {len(table_id_matches)} table IDs found")
                        print(f"✅ Content loaded after {delay}s - table IDs detected")
                        content_loaded = True
                        break
                    
                    logger.info(f"Content not ready after {delay}s, trying next delay...")
            
            if content_loaded:
                # Give a small additional delay to ensure everything is fully rendered
                time.sleep(0.2)  # Short final delay for player history
                logger.info("Player history content loading completed successfully")
                return True
            else:
                logger.warning(f"Player history content failed to load within timeout for player {player_id}")
                print("⚠️  Player history content loading timeout - proceeding anyway")
                
                # Even if we timeout, let's try to proceed - sometimes content is there but not detected
                return True
                
        except Exception as e:
            logger.error(f"Error waiting for player history content to load: {e}")
            print(f"❌ Error waiting for player history content: {e}")
            # Don't fail completely - try to proceed
            return True

    def _wait_for_gamereview_content_to_load(self, table_id: str) -> bool:
        """
        Wait for the gamereview page JavaScript content to load properly
        
        Args:
            table_id: BGA table ID for logging purposes
            
        Returns:
            bool: True if content loaded successfully, False if timeout or error
        """
        try:
            # Get timeout from speed settings
            timeout = self.speed_settings.get('element_wait_timeout', 10)
            
            print(f"⏱️  Waiting for JavaScript content to load (timeout: {timeout}s)")
            logger.info(f"Waiting for gamereview content to load for table {table_id}")
            
            # Strategy 1: Wait for specific content indicators to appear
            wait = WebDriverWait(self.driver, timeout)
            
            # Try multiple strategies to detect when content is loaded
            content_loaded = False
            
            # Strategy 1: Wait for replay links to appear
            try:
                logger.info("Strategy 1: Waiting for replay links to appear...")
                wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/archive/replay/')]")))
                logger.info("Replay links found - content appears to be loaded")
                print("✅ Replay links detected - content loaded")
                content_loaded = True
            except:
                logger.info("Strategy 1 failed: No replay links found")
            
            # Strategy 2: Wait for player selection elements (common in gamereview pages)
            if not content_loaded:
                try:
                    logger.info("Strategy 2: Waiting for player selection elements...")
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.playerselection, div.score-entry")))
                    logger.info("Player selection elements found")
                    print("✅ Player selection elements detected - content loaded")
                    content_loaded = True
                except:
                    logger.info("Strategy 2 failed: No player selection elements found")
            
            # Strategy 3: Wait for overall-content div to be populated
            if not content_loaded:
                try:
                    logger.info("Strategy 3: Waiting for overall-content to be populated...")
                    
                    def content_populated(driver):
                        try:
                            overall_content = driver.find_element(By.ID, "overall-content")
                            # Check if it has meaningful content (not just empty or minimal)
                            content_text = overall_content.text.strip()
                            inner_html = overall_content.get_attribute('innerHTML').strip()
                            
                            # Content is considered loaded if:
                            # 1. It has substantial text content, OR
                            # 2. It has substantial HTML content with meaningful elements
                            has_text = len(content_text) > 100
                            has_html = len(inner_html) > 1000 and ('playerselection' in inner_html or 'archive/replay' in inner_html)
                            
                            if has_text or has_html:
                                logger.info(f"Overall-content populated: text={len(content_text)} chars, html={len(inner_html)} chars")
                                return True
                            return False
                        except:
                            return False
                    
                    wait.until(content_populated)
                    logger.info("Overall-content div populated with meaningful content")
                    print("✅ Page content populated - content loaded")
                    content_loaded = True
                except:
                    logger.info("Strategy 3 failed: Overall-content not populated")
            
            # Strategy 4: Progressive delay with content checks
            if not content_loaded:
                logger.info("Strategy 4: Using progressive delays with content validation...")
                delays = [1.0, 2.0, 3.0, 5.0]  # Progressive delays
                
                for delay in delays:
                    print(f"⏱️  Waiting {delay}s for content to load...")
                    time.sleep(delay)
                    
                    # Check if content has appeared
                    page_source = self.driver.page_source
                    
                    # Look for replay URLs in the page source
                    if '/archive/replay/' in page_source and re.search(r'/archive/replay/\d{6}-\d{4}/', page_source):
                        logger.info(f"Content loaded after {delay}s delay - replay URLs found")
                        print(f"✅ Content loaded after {delay}s - replay URLs detected")
                        content_loaded = True
                        break
                    
                    # Look for substantial content in overall-content div
                    try:
                        soup = BeautifulSoup(page_source, 'html.parser')
                        overall_content = soup.find('div', id='overall-content')
                        if overall_content:
                            content_text = overall_content.get_text().strip()
                            if len(content_text) > 100:
                                logger.info(f"Content loaded after {delay}s delay - substantial text found")
                                print(f"✅ Content loaded after {delay}s - page content detected")
                                content_loaded = True
                                break
                    except:
                        pass
                    
                    logger.info(f"Content not ready after {delay}s, trying next delay...")
            
            if content_loaded:
                # Give a small additional delay to ensure everything is fully rendered
                time.sleep(0.5)
                logger.info("Content loading completed successfully")
                return True
            else:
                logger.warning(f"Content failed to load within timeout for table {table_id}")
                print("⚠️  Content loading timeout - proceeding anyway")
                
                # Even if we timeout, let's try to proceed - sometimes content is there but not detected
                return True
                
        except Exception as e:
            logger.error(f"Error waiting for content to load: {e}")
            print(f"❌ Error waiting for content: {e}")
            # Don't fail completely - try to proceed
            return True

    def _wait_for_replay_content_to_load(self, replay_id: str) -> bool:
        """
        Wait for the replay page content to load properly, specifically focusing on g_gamelogs
        
        Args:
            replay_id: BGA replay ID for logging purposes
            
        Returns:
            bool: True if content loaded successfully, False if timeout or error
        """
        try:
            # Get timeout from speed settings
            timeout = self.speed_settings.get('element_wait_timeout', 10)
            
            print(f"⏱️  Waiting for replay content to load (timeout: {timeout}s)")
            logger.info(f"Waiting for replay content to load for replay {replay_id}")
            
            # Strategy 1: Wait for specific content indicators to appear
            wait = WebDriverWait(self.driver, timeout)
            
            # Try multiple strategies to detect when content is loaded
            content_loaded = False
            
            # Strategy 1: Wait for g_gamelogs JavaScript variable to be populated
            try:
                logger.info("Strategy 1: Waiting for g_gamelogs JavaScript variable...")
                
                def gamelogs_populated(driver):
                    try:
                        # Execute JavaScript to check if g_gamelogs exists and has content
                        result = driver.execute_script("""
                            if (typeof g_gamelogs !== 'undefined' && g_gamelogs && g_gamelogs.length > 0) {
                                return g_gamelogs.length;
                            }
                            return 0;
                        """)
                        
                        if result and result > 0:
                            logger.info(f"Found g_gamelogs with {result} entries")
                            return True
                        return False
                    except Exception as e:
                        logger.debug(f"Error checking g_gamelogs: {e}")
                        return False
                
                wait.until(gamelogs_populated)
                logger.info("g_gamelogs JavaScript variable populated - content appears to be loaded")
                print("✅ g_gamelogs detected - content loaded")
                content_loaded = True
            except:
                logger.info("Strategy 1 failed: g_gamelogs not found or not populated")
            
            # Strategy 2: Wait for replay log DOM elements to appear
            if not content_loaded:
                try:
                    logger.info("Strategy 2: Waiting for replay log elements...")
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.replaylogs_move")))
                    
                    # Verify we have multiple log entries (typical replay has many moves)
                    log_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.replaylogs_move")
                    if len(log_elements) >= 1:  # At least one move
                        logger.info(f"Found {len(log_elements)} replay log elements - content appears loaded")
                        print(f"✅ Replay logs detected ({len(log_elements)} moves) - content loaded")
                        content_loaded = True
                    else:
                        logger.info(f"Only found {len(log_elements)} replay log elements - waiting for more")
                except:
                    logger.info("Strategy 2 failed: No replay log elements found")
            
            # Strategy 3: Wait for player selection or game interface elements
            if not content_loaded:
                try:
                    logger.info("Strategy 3: Waiting for player selection elements...")
                    wait.until(EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.playerselection")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.player_board")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "span.playername"))
                    ))
                    logger.info("Player interface elements found")
                    print("✅ Player interface detected - content loaded")
                    content_loaded = True
                except:
                    logger.info("Strategy 3 failed: No player interface elements found")
            
            # Strategy 4: Wait for overall-content div to be populated with replay-specific content
            if not content_loaded:
                try:
                    logger.info("Strategy 4: Waiting for overall-content to be populated with replay content...")
                    
                    def replay_content_populated(driver):
                        try:
                            overall_content = driver.find_element(By.ID, "overall-content")
                            content_text = overall_content.text.strip()
                            inner_html = overall_content.get_attribute('innerHTML').strip()
                            
                            # Content is considered loaded if:
                            # 1. It has substantial text content, AND
                            # 2. It contains replay-specific indicators
                            has_text = len(content_text) > 200
                            has_replay_content = any(indicator in inner_html.lower() for indicator in [
                                'replaylogs', 'playername', 'playerselection', 'g_gamelogs'
                            ])
                            
                            if has_text and has_replay_content:
                                logger.info(f"Replay content populated: text={len(content_text)} chars, has_replay_content={has_replay_content}")
                                return True
                            return False
                        except:
                            return False
                    
                    wait.until(replay_content_populated)
                    logger.info("Overall-content div populated with replay content")
                    print("✅ Replay content populated - content loaded")
                    content_loaded = True
                except:
                    logger.info("Strategy 4 failed: Overall-content not populated with replay content")
            
            # Strategy 5: Progressive delay with content validation (fallback)
            if not content_loaded:
                logger.info("Strategy 5: Using progressive delays with content validation...")
                delays = [1.0, 2.0, 3.0, 5.0]  # Progressive delays for replay pages
                
                for delay in delays:
                    print(f"⏱️  Waiting {delay}s for content to load...")
                    time.sleep(delay)
                    
                    # Check if content has appeared
                    page_source = self.driver.page_source
                    
                    # Look for g_gamelogs in the page source
                    if 'g_gamelogs' in page_source and 'replaylogs_move' in page_source:
                        logger.info(f"Content loaded after {delay}s delay - g_gamelogs and replay logs found")
                        print(f"✅ Content loaded after {delay}s - replay data detected")
                        content_loaded = True
                        break
                    
                    # Look for replay log elements
                    try:
                        soup = BeautifulSoup(page_source, 'html.parser')
                        replay_logs = soup.find_all('div', class_='replaylogs_move')
                        if len(replay_logs) >= 1:
                            logger.info(f"Content loaded after {delay}s delay - {len(replay_logs)} replay logs found")
                            print(f"✅ Content loaded after {delay}s - replay logs detected")
                            content_loaded = True
                            break
                    except:
                        pass
                    
                    # Check for substantial content with replay indicators
                    if any(indicator in page_source.lower() for indicator in [
                        'replaylogs', 'g_gamelogs', 'playerselection'
                    ]) and len(page_source) > 10000:
                        logger.info(f"Content loaded after {delay}s delay - replay indicators found")
                        print(f"✅ Content loaded after {delay}s - replay indicators detected")
                        content_loaded = True
                        break
                    
                    logger.info(f"Content not ready after {delay}s, trying next delay...")
            
            if content_loaded:
                # Give a small additional delay to ensure everything is fully rendered
                time.sleep(0.3)  # Short final delay for replay pages
                logger.info("Replay content loading completed successfully")
                return True
            else:
                logger.warning(f"Replay content failed to load within timeout for replay {replay_id}")
                print("⚠️  Replay content loading timeout - proceeding anyway")
                
                # Even if we timeout, let's try to proceed - sometimes content is there but not detected
                return True
                
        except Exception as e:
            logger.error(f"Error waiting for replay content to load: {e}")
            print(f"❌ Error waiting for replay content: {e}")
            # Don't fail completely - try to proceed
            return True

    def scrape_replay_from_table(self, table_id: str, player_id: str, save_raw: bool = True, raw_data_dir: str = None, version_id: str = None, player_perspective: str = None) -> Optional[Dict]:
        """
        Scrape replay page using table ID and player ID with optional version parameter
        
        Args:
            table_id: BGA table ID
            player_id: Player ID for replay URL construction
            save_raw: Whether to save raw HTML
            raw_data_dir: Directory to save raw HTML files
            version_id: Optional version ID to use (if not provided, will extract from gamereview)
            player_perspective: Optional player perspective for file organization (if different from player_id)
            
        Returns:
            dict: Replay data or None if failed
        """
        if raw_data_dir is None:
            raw_data_dir = config.RAW_DATA_DIR
        
        # Use provided version or extract from gamereview
        if version_id:
            logger.info(f"Using provided version: {version_id}")
        else:
            logger.info("No version provided, extracting from gamereview...")
            version_id = self.extract_version_from_gamereview(table_id)
        
        from config import REPLAY_URL_TEMPLATE
        replay_url = REPLAY_URL_TEMPLATE.format(version_id=version_id, table_id=table_id, player_id=player_id)

        logger.info(f"Scraping replay page: {replay_url}")
        
        # Pass player_perspective to scrape_replay for proper file organization
        return self.scrape_replay(replay_url, save_raw, raw_data_dir, player_perspective)

    def scrape_replay_only_with_metadata(self, table_id: str, version_id: str, player_perspective: str, save_raw: bool = False, raw_data_dir: str = None) -> Optional[Dict]:
        """
        Scrape only the replay page using provided metadata (no table scraping needed)
        Optimized for replay scraping assignments where table data already exists
        
        Args:
            table_id: BGA table ID
            version_id: Version ID for replay URL (from assignment)
            player_perspective: Player ID for replay URL construction (from assignment)
            save_raw: Whether to save raw HTML (default False for memory-only mode)
            raw_data_dir: Directory to save raw HTML files (optional)
            
        Returns:
            dict: Replay data with daily limit detection, or None if failed
        """
        logger.info(f"Scraping replay only for game {table_id} with version {version_id}")
        
        try:
            # Construct replay URL using provided metadata
            if hasattr(config, 'REPLAY_URL_TEMPLATE'):
                replay_url = config.REPLAY_URL_TEMPLATE.format(
                    version_id=version_id, 
                    table_id=table_id, 
                    player_id=player_perspective
                )
            else:
                # Fallback URL construction
                replay_url = f"https://boardgamearena.com/archive/replay/{version_id}/?table={table_id}&player={player_perspective}&comments={player_perspective}"
            
            logger.info(f"Constructed replay URL: {replay_url}")
            
            # Scrape the replay page directly
            replay_result = self.scrape_replay(replay_url, save_raw, raw_data_dir, player_perspective)
            
            if replay_result:
                # Add metadata to result for tracking
                replay_result['table_id'] = table_id
                replay_result['version_id'] = version_id
                replay_result['player_perspective'] = player_perspective
                replay_result['replay_only_mode'] = True
                
                logger.info(f"Successfully scraped replay-only for game {table_id}")
                return replay_result
            else:
                logger.warning(f"Failed to scrape replay for game {table_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error in replay-only scraping for game {table_id}: {e}")
            return None

    def scrape_replay(self, url: str, save_raw: bool = True, raw_data_dir: str = None, player_perspective: str = None) -> Optional[Dict]:
        """
        Scrape a single replay page
        
        Args:
            url: BGA replay URL
            save_raw: Whether to save raw HTML
            raw_data_dir: Directory to save raw HTML files
            player_perspective: Optional player perspective for file organization (overrides URL extraction)
            
        Returns:
            dict: Scraped data or None if failed
        """
        # Handle memory-only mode
        if raw_data_dir is None and hasattr(config, 'RAW_DATA_DIR'):
            raw_data_dir = config.RAW_DATA_DIR
            
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        # Extract replay ID from URL
        replay_id = self._extract_replay_id(url)
        if not replay_id:
            logger.error(f"Could not extract replay ID from {url}")
            return None
        
        logger.info(f"Scraping replay {replay_id}")
        
        try:
            # Navigate to the replay URL
            print(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for replay content to load using smart detection instead of fixed delay
            if not self._wait_for_replay_content_to_load(replay_id):
                print("❌ Replay content failed to load properly")
                # Continue anyway - sometimes content is there but not detected
            
            # Check if we got an error page
            page_source = self.driver.page_source
            
            # Check for replay limit reached
            if self._check_replay_limit_reached(page_source):
                logger.warning(f"Replay limit reached when accessing {url}")
                print("🚫 You have reached your daily replay limit!")
                print("   BGA has daily limits on replay access to prevent server overload.")
                print("   Please try again tomorrow or wait for the limit to reset.")
                return {
                    'replay_id': replay_id,
                    'url': url,
                    'scraped_at': datetime.now().isoformat(),
                    'error': 'replay_limit_reached',
                    'limit_reached': True
                }
            
            # Check for authentication errors - but first check if it's actually a daily limit issue
            if 'must be logged' in page_source.lower() or 'fatalerror' in page_source.lower():
                # Before trying to re-authenticate, check if this is actually a daily limit issue
                # Sometimes BGA shows auth errors when the daily limit is reached
                if self._check_replay_limit_reached(page_source):
                    logger.warning(f"Daily replay limit reached (detected via auth error page) when accessing {url}")
                    print("🚫 Daily replay limit reached!")
                    print("   BGA sometimes shows authentication errors when the daily limit is reached.")
                    print("   Please try again tomorrow or wait for the limit to reset.")
                    return {
                        'replay_id': replay_id,
                        'url': url,
                        'scraped_at': datetime.now().isoformat(),
                        'error': 'replay_limit_reached',
                        'limit_reached': True
                    }
                
                logger.warning("Authentication error detected, attempting re-authentication...")
                print("⚠️  Session expired! Attempting to re-authenticate...")
                
                # Try to re-authenticate using session or fallback to manual
                if not self.refresh_authentication():
                    print("❌ Authentication refresh failed")
                    return None
                
                # Retry the replay page
                print(f"Retrying replay page: {url}")
                self.driver.get(url)
                time.sleep(5)
                
                # Check again
                page_source = self.driver.page_source
                if 'must be logged' in page_source.lower() or 'fatalerror' in page_source.lower():
                    # Check one more time if this is a daily limit issue after retry
                    if self._check_replay_limit_reached(page_source):
                        logger.warning(f"Daily replay limit reached (detected after retry) when accessing {url}")
                        print("🚫 Daily replay limit reached after retry!")
                        return {
                            'replay_id': replay_id,
                            'url': url,
                            'scraped_at': datetime.now().isoformat(),
                            'error': 'replay_limit_reached',
                            'limit_reached': True
                        }
                    print("❌ Authentication failed even after re-authentication")
                    return None
                else:
                    print("✅ Re-authentication successful!")
            
            if 'fatal error' in page_source.lower() and 'must be logged' not in page_source.lower():
                print("❌ Fatal error on page - replay might not be accessible")
                return None
            
            # Save raw HTML if requested and raw_data_dir is provided
            if save_raw and raw_data_dir:
                # Use provided player_perspective or extract from URL as fallback
                if not player_perspective:
                    from urllib.parse import urlparse, parse_qs
                    parsed_url = urlparse(url)
                    query_params = parse_qs(parsed_url.query)
                    player_perspective = query_params.get('player', [None])[0]
                
                if player_perspective:
                    # Create player perspective directory
                    player_raw_dir = os.path.join(raw_data_dir, player_perspective)
                    os.makedirs(player_raw_dir, exist_ok=True)
                    raw_file_path = os.path.join(player_raw_dir, f"replay_{replay_id}.html")
                else:
                    # Fallback to root directory if no player perspective found
                    os.makedirs(raw_data_dir, exist_ok=True)
                    raw_file_path = os.path.join(raw_data_dir, f"replay_{replay_id}.html")
                
                with open(raw_file_path, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                logger.info(f"Saved raw HTML to {raw_file_path}")
            
            # Parse the HTML to extract basic information
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract basic replay information
            replay_data = {
                'replay_id': replay_id,
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'title': None,
                'players': [],
                'game_logs_found': False,
                'html_content': page_source  # Always include HTML content for memory-only mode
            }
            
            # Try to extract title
            title_elem = soup.find('title')
            if title_elem:
                replay_data['title'] = title_elem.get_text().strip()

            # Look for game logs section
            game_logs = soup.find_all('div', class_='replaylogs_move')
            if game_logs:
                replay_data['game_logs_found'] = True
                replay_data['num_moves'] = len(game_logs)
                logger.info(f"Found {len(game_logs)} game log entries")
                print(f"✅ Found {len(game_logs)} game log entries")
            else:
                logger.warning("No game logs found in replay")
                print("⚠️  No game logs found - checking page content...")
                
                # Debug: check what we actually got
                if len(page_source) < 1000:
                    print(f"Page seems too short ({len(page_source)} chars)")
                    print("First 500 chars:", page_source[:500])
            
            # Try to extract player information
            player_elements = soup.find_all('span', class_='playername')
            for player_elem in player_elements:
                player_name = player_elem.get_text().strip()
                if player_name:
                    replay_data['players'].append(player_name)

            logger.info(f"Successfully scraped replay {replay_id}")
            return replay_data
            
        except Exception as e:
            logger.error(f"Error scraping replay {replay_id}: {e}")
            print(f"❌ Error scraping replay: {e}")
            return None
    
    def scrape_player_game_history(self, player_id: str, max_clicks: int = 1000, 
                                 click_delay: Optional[float] = None) -> List[Dict]:
        """
        Scrape all table IDs and datetimes from a player's game history by auto-clicking "See more"
        
        Args:
            player_id: BGA player ID
            max_clicks: Maximum number of "See more" clicks to prevent infinite loops
            click_delay: Delay between clicks in seconds (uses speed profile if None)
            
        Returns:
            list: List of dictionaries containing table_id, raw_datetime, parsed_datetime, and date_type
        """
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        # Use speed profile click delay if not specified
        if click_delay is None:
            click_delay = self.speed_settings.get('click_delay', 0.5)
        
        # Construct player history URL - this may need to be adjusted based on actual BGA URL pattern
        player_url = f"https://boardgamearena.com/gamestats?player={player_id}&opponent_id=0&game_id={TERRAFORMING_MARS_GAME_ID}&finished=1"        
        logger.info(f"Scraping game history for player {player_id}")
        
        try:
            # Navigate to player page
            print(f"Navigating to player page: {player_url}")
            self.driver.get(player_url)
            
            # Wait for content to load using smart detection instead of fixed delay
            if not self._wait_for_player_history_content_to_load(player_id):
                print("❌ Player history content failed to load properly")
                return []
            
            # Get the page source after content has loaded
            page_source = self.driver.page_source
            
            click_count = 0
            games_loaded = 0
            
            print("Starting to load all games by clicking 'See more'...")
            
            while click_count < max_clicks:
                # Primary strategy: Look for the specific ID "see_more_tables"
                see_more_element = None
                
                see_more_element = self.driver.find_element(By.ID, "see_more_tables")

                # If no element found, break
                if not see_more_element:
                    print("No 'See more' button found - all games may be loaded")
                    # Save current page source for debugging
                    if click_count == 0:
                        print("Saving page source for debugging...")
                        with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        print("Page source saved to debug_page_source.html")
                    break
                
                # Try to click the found element
                try:
                    # Scroll to element to make sure it's visible
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", see_more_element)
                    time.sleep(1)
                    
                    see_more_element.click()
                    
                    click_count += 1
                    print(f"Clicked 'See more' #{click_count}, waiting for content to load...")
                    time.sleep(click_delay)
                    
                    # Check for "No more results" message
                    no_more_results = self.driver.find_elements(By.XPATH, 
                        "//*[contains(text(), 'No more results')]")
                    
                    if no_more_results:
                        print("✅ 'No more results' detected - all games loaded!")
                        break
                    
                    games_loaded += 10
                    print(f"Progress: ~{games_loaded} games loaded so far...")
                    
                except Exception as e:
                    logger.warning(f"Error clicking 'See more' button: {e}")
                    print(f"⚠️  Error clicking 'See more': {e}")
                    print(f"Element tag: {see_more_element.tag_name}, text: '{see_more_element.text}'")
                    break
            
            if click_count >= max_clicks:
                print(f"⚠️  Reached maximum click limit ({max_clicks}). Some games might not be loaded.")
            
            # Extract table IDs and datetimes from the fully loaded page
            print("Extracting table IDs and datetimes from loaded page...")
            page_source = self.driver.page_source
            game_data = self._extract_games_with_datetimes_from_history(page_source)
            
            
            logger.info(f"Successfully extracted {len(game_data)} games with datetimes from player {player_id}")
            print(f"✅ Found {len(game_data)} games with datetimes for player {player_id}")
            
            return game_data
            
        except Exception as e:
            logger.error(f"Error scraping player game history for {player_id}: {e}")
            print(f"❌ Error scraping player game history: {e}")
            return []    

    def _extract_games_with_datetimes_from_history(self, html_content: str) -> List[Dict]:
        """
        Extract table IDs and datetimes from player game history HTML
        
        Args:
            html_content: HTML content of the player history page
            
        Returns:
            list: List of dictionaries containing table_id, raw_datetime, parsed_datetime, and date_type
        """
        games_data = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for game rows - each row should contain both table ID and datetime
            game_rows = soup.find_all('tr')  # Table rows
            if not game_rows:
                # Fallback: look for div rows
                game_rows = soup.find_all('div', class_='row')
            
            logger.info(f"Found {len(game_rows)} potential game rows")
            
            for row in game_rows:
                try:
                    # Extract table ID from this row
                    table_id_match = re.search(r'#(\d{8,})', str(row))
                    if not table_id_match:
                        continue
                    
                    table_id = table_id_match.group(1)
                    
                    # Extract datetime from this row
                    datetime_info = self._extract_datetime_from_row(row)
                    if not datetime_info:
                        # If no datetime found, create a basic entry
                        datetime_info = {
                            'raw_datetime': 'unknown',
                            'parsed_datetime': None,
                            'date_type': 'unknown'
                        }
                    
                    game_data = {
                        'table_id': table_id,
                        'raw_datetime': datetime_info['raw_datetime'],
                        'parsed_datetime': datetime_info['parsed_datetime'],
                        'date_type': datetime_info['date_type']
                    }
                    
                    games_data.append(game_data)
                    logger.debug(f"Extracted game {table_id} with datetime: {datetime_info['raw_datetime']}")
                    
                except Exception as e:
                    logger.debug(f"Error processing game row: {e}")
                    continue
            
            # Remove duplicates while preserving order
            unique_games = []
            seen_table_ids = set()
            for game in games_data:
                table_id = game['table_id']
                if table_id not in seen_table_ids and len(table_id) >= 8:
                    unique_games.append(game)
                    seen_table_ids.add(table_id)
            
            logger.info(f"Extracted {len(unique_games)} unique games with datetimes")
            return unique_games
            
        except Exception as e:
            logger.error(f"Error extracting games with datetimes from history: {e}")
            return []

    def _extract_datetime_from_row(self, row) -> Optional[Dict]:
        """
        Extract datetime information from a game row
        
        Args:
            row: BeautifulSoup element representing a game row
            
        Returns:
            dict: Dictionary with raw_datetime, parsed_datetime, and date_type, or None if not found
        """
        try:
            # Look for datetime in smalltext elements (common pattern in BGA)
            smalltext_elements = row.find_all('div', class_='smalltext')
            
            for elem in smalltext_elements:
                text = elem.get_text().strip()
                datetime_info = self._parse_game_datetime(text)
                if datetime_info:
                    return datetime_info
            
            # Fallback: look for datetime patterns in any text within the row
            row_text = row.get_text()
            datetime_info = self._parse_game_datetime(row_text)
            if datetime_info:
                return datetime_info
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting datetime from row: {e}")
            return None


    def _parse_game_datetime(self, text: str) -> Optional[Dict]:
        """
        Parse datetime from text, handling both relative and absolute dates
        
        Args:
            text: Text that may contain datetime information
            
        Returns:
            dict: Dictionary with raw_datetime, parsed_datetime, and date_type, or None if not found
        """
        try:
            # Pattern 1: Relative dates like "yesterday at 00:08"
            relative_pattern = r'(yesterday|today)\s+at\s+(\d{1,2}:\d{2})'
            relative_match = re.search(relative_pattern, text.lower())
            
            if relative_match:
                relative_word = relative_match.group(1)
                time_str = relative_match.group(2)
                
                # Calculate the actual date
                current_date = datetime.now()
                if relative_word == 'yesterday':
                    target_date = current_date - timedelta(days=1)
                else:  # today
                    target_date = current_date
                
                # Parse the time
                time_parts = time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                # Create the full datetime
                parsed_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                return {
                    'raw_datetime': f"{relative_word} at {time_str}",
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date_type': 'relative'
                }
            
            # Pattern 2: Absolute dates like "2025-06-15 at 00:29"
            absolute_pattern = r'(\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2}:\d{2})'
            absolute_match = re.search(absolute_pattern, text)
            
            if absolute_match:
                date_str = absolute_match.group(1)
                time_str = absolute_match.group(2)
                
                # Parse the full datetime
                datetime_str = f"{date_str} {time_str}:00"
                parsed_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                
                return {
                    'raw_datetime': f"{date_str} at {time_str}",
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date_type': 'absolute'
                }
            
            # Pattern 3: Alternative absolute format like "15/06/2025 at 00:29"
            alt_absolute_pattern = r'(\d{1,2}/\d{1,2}/\d{4})\s+at\s+(\d{1,2}:\d{2})'
            alt_absolute_match = re.search(alt_absolute_pattern, text)
            
            if alt_absolute_match:
                date_str = alt_absolute_match.group(1)
                time_str = alt_absolute_match.group(2)
                
                # Parse the date (assuming DD/MM/YYYY format)
                date_parts = date_str.split('/')
                day = int(date_parts[0])
                month = int(date_parts[1])
                year = int(date_parts[2])
                
                # Parse the time
                time_parts = time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                # Create the datetime
                parsed_datetime = datetime(year, month, day, hour, minute, 0)
                
                return {
                    'raw_datetime': f"{date_str} at {time_str}",
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date_type': 'absolute'
                }
            
            # Pattern 4: Just time like "00:08" (assume today)
            time_only_pattern = r'\b(\d{1,2}:\d{2})\b'
            time_only_match = re.search(time_only_pattern, text)
            
            if time_only_match:
                time_str = time_only_match.group(1)
                
                # Parse the time and assume today
                time_parts = time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                current_date = datetime.now()
                parsed_datetime = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                return {
                    'raw_datetime': time_str,
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date_type': 'time_only'
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing datetime from text '{text}': {e}")
            return None

    def initialize_session(self) -> bool:
        """
        Initialize authenticated session for direct HTTP requests
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.email or not self.password:
            logger.error("Email and password are required for session initialization")
            return False
        
        try:
            # Initialize session to get cookies
            if not self.session:
                print("🔐 Initializing session for direct requests...")
                self.session = BGASession(
                    email=self.email,
                    password=self.password,
                    chromedriver_path=self.chromedriver_path,
                    chrome_path=self.chrome_path,
                    headless=True  # Use headless for session-only initialization
                )
                
                if not self.session.login():
                    logger.error("Session initialization failed")
                    return False
            
            # Create requests session and copy cookies
            self.requests_session = requests.Session()
            
            # Get cookies from the browser session
            if self.session.driver:
                cookies = self.session.driver.get_cookies()
                for cookie in cookies:
                    self.requests_session.cookies.set(
                        cookie['name'], 
                        cookie['value'], 
                        domain=cookie.get('domain', '.boardgamearena.com')
                    )
                logger.info(f"Copied {len(cookies)} cookies to requests session")
            
            # Set appropriate headers
            self.requests_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            print("✅ Session initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            return False

    def fetch_replay_direct(self, table_id: str, version: str, player_id: str,
                           save_raw: bool = True, raw_data_dir: str = None) -> Optional[Dict]:
        """
        Fetch replay HTML directly using requests session (no browser needed)
        
        Args:
            table_id: BGA table ID
            version: Version number for replay URL
            player_id: Player ID for replay URL construction
            save_raw: Whether to save raw HTML
            raw_data_dir: Directory to save raw HTML files
            
        Returns:
            dict: Replay data or None if failed
        """
        if raw_data_dir is None:
            raw_data_dir = config.RAW_DATA_DIR
        if not self.requests_session:
            logger.error("Requests session not initialized. Call initialize_session() first.")
            return None
        
        # Construct replay URL
        replay_url = f"https://boardgamearena.com/archive/replay/{version}/?table={table_id}&player={player_id}&comments={player_id}"
        logger.info(f"Fetching replay directly: {replay_url}")
        
        try:
            print(f"🌐 Fetching replay via HTTP: {replay_url}")
            
            # Make the request
            response = self.requests_session.get(replay_url, timeout=30)
            response.raise_for_status()
            
            page_source = response.text
            logger.info(f"Successfully fetched replay HTML ({len(page_source)} chars)")
            
            # Check for authentication errors
            if 'must be logged' in page_source.lower():
                logger.warning("Authentication error in direct fetch")
                print("❌ Authentication error - session may have expired")
                return None
            
            # Check for replay limit
            if self._check_replay_limit_reached(page_source):
                logger.warning(f"Replay limit reached when fetching {replay_url}")
                print("🚫 You have reached your daily replay limit!")
                return {
                    'replay_id': table_id,
                    'url': replay_url,
                    'scraped_at': datetime.now().isoformat(),
                    'error': 'replay_limit_reached',
                    'limit_reached': True,
                    'direct_fetch': True
                }
            
            # Save raw HTML if requested
            if save_raw:
                os.makedirs(raw_data_dir, exist_ok=True)
                raw_file_path = os.path.join(raw_data_dir, f"replay_{table_id}.html")
                
                with open(raw_file_path, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                logger.info(f"Saved raw HTML to {raw_file_path}")
            
            # Parse the HTML to extract basic information
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract basic replay information
            replay_data = {
                'replay_id': table_id,
                'url': replay_url,
                'scraped_at': datetime.now().isoformat(),
                'title': None,
                'players': [],
                'game_logs_found': False,
                'direct_fetch': True  # Flag to indicate this was direct fetching
            }
            
            # Try to extract title
            title_elem = soup.find('title')
            if title_elem:
                replay_data['title'] = title_elem.get_text().strip()
            
            # Look for game logs section
            game_logs = soup.find_all('div', class_='replaylogs_move')
            if game_logs:
                replay_data['game_logs_found'] = True
                replay_data['num_moves'] = len(game_logs)
                logger.info(f"Found {len(game_logs)} game log entries")
                print(f"✅ Found {len(game_logs)} game log entries (direct fetch)")
            else:
                logger.warning("No game logs found in replay")
                print("⚠️  No game logs found in direct fetch")
            
            # Try to extract player information
            player_elements = soup.find_all('span', class_='playername')
            for player_elem in player_elements:
                player_name = player_elem.get_text().strip()
                if player_name:
                    replay_data['players'].append(player_name)
            
            logger.info(f"Successfully fetched replay {table_id} via direct HTTP")
            print(f"✅ Direct fetch successful for replay {table_id}")
            return replay_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching replay {table_id}: {e}")
            print(f"❌ HTTP error fetching replay: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in direct replay fetch for {table_id}: {e}")
            print(f"❌ Error in direct fetch: {e}")
            return None

    def can_use_direct_fetch(self, table_id: str, raw_data_dir: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if we can use direct fetching for a game (table HTML exists + version available)
        
        Args:
            table_id: BGA table ID
            raw_data_dir: Directory where raw HTML files are stored
            
        Returns:
            tuple: (can_use_direct, version, player_id) where:
                - can_use_direct: bool indicating if direct fetch is possible
                - version: version number if available, None otherwise
                - player_id: first player ID if available, None otherwise
        """
        if raw_data_dir is None:
            raw_data_dir = config.RAW_DATA_DIR
        try:
            # Check if table HTML file exists
            table_html_path = os.path.join(raw_data_dir, f"table_{table_id}.html")
            if not os.path.exists(table_html_path):
                logger.debug(f"Table HTML not found for {table_id}")
                return False, None, None
            
            # Read table HTML to extract player IDs and check for version in registry
            with open(table_html_path, 'r', encoding='utf-8') as f:
                table_html = f.read()
            
            # Extract player IDs from table HTML
            player_ids = self.extract_player_ids_from_table(table_html)
            if not player_ids:
                logger.debug(f"No player IDs found in table HTML for {table_id}")
                return False, None, None
            
            # Check if version is available in games registry
            from .games_registry import GamesRegistry
            games_registry = GamesRegistry()
            game_info = games_registry.get_game_info(table_id)
            
            if not game_info or not game_info.get('version'):
                logger.debug(f"No version found in registry for {table_id}")
                return False, None, None
            
            version = game_info['version']
            player_id = player_ids[0]  # Use first player ID
            
            logger.info(f"Direct fetch possible for {table_id}: version={version}, player_id={player_id}")
            return True, version, player_id
            
        except Exception as e:
            logger.error(f"Error checking direct fetch capability for {table_id}: {e}")
            return False, None, None

    def close_browser(self):
        """Close the browser and cleanup session"""
        if self.session:
            try:
                self.session.close_browser()
                print("Browser closed via session")
            except:
                pass
            finally:
                self.session = None
                self.driver = None
        elif self.driver:
            try:
                self.driver.quit()
                print("Browser closed")
            except:
                pass
            finally:
                self.driver = None
        
        # Close requests session
        if self.requests_session:
            try:
                self.requests_session.close()
                logger.info("Requests session closed")
            except:
                pass
            finally:
                self.requests_session = None

    def refresh_authentication(self) -> bool:
        """
        Refresh authentication when session expires
        
        Returns:
            bool: True if refresh successful, False otherwise
        """
        if self.session:
            logger.info("Refreshing session authentication...")
            print("🔄 Refreshing authentication...")
            
            try:
                if self.session.refresh_authentication():
                    self.driver = self.session.get_driver()
                    print("✅ Authentication refreshed successfully!")
                    return True
                else:
                    print("❌ Authentication refresh failed")
                    return False
            except Exception as e:
                logger.error(f"Error refreshing authentication: {e}")
                print(f"❌ Error refreshing authentication: {e}")
                return False
        else:
            logger.warning("No session available for refresh")
            print("⚠️  No session available - falling back to manual login")
            return self.login_to_bga()
    
    def _check_replay_limit_reached(self, page_source: str) -> bool:
        """
        Check if the replay limit has been reached based on page content
        
        Args:
            page_source: HTML content of the page
            
        Returns:
            bool: True if replay limit reached, False otherwise
        """
        try:
            # Convert to lowercase for case-insensitive matching
            page_content = page_source.lower()
            
            # Check for the specific limit message patterns
            limit_indicators = [
                'you have reached a limit (replay)',
                'you have reached a limit',
                'reached a limit (replay)',
                'reached a limit',
                'replay limit',
                'limit reached',
                'daily replay limit'
            ]
            
            for indicator in limit_indicators:
                if indicator in page_content:
                    logger.info(f"Replay limit detected: found '{indicator}' in page content")
                    return True
            
            # Also check for the limit notification in structured content
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Look for notification elements that might contain limit messages
                notification_selectors = [
                    'div.notification',
                    'div.alert',
                    'div.error',
                    'div.warning',
                    '.limit-message',
                    '[class*="limit"]',
                    '[class*="notification"]'
                ]
                
                for selector in notification_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        element_text = element.get_text().lower()
                        if any(indicator in element_text for indicator in limit_indicators):
                            logger.info(f"Replay limit detected in notification element: {element_text[:100]}")
                            return True
                
            except Exception as e:
                logger.debug(f"Error parsing HTML for limit detection: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking replay limit: {e}")
            return False

    def _extract_replay_id(self, url: str) -> Optional[str]:
        """Extract replay ID from BGA replay URL (table parameter)"""
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            
            # Extract the table parameter from query string
            query_params = parse_qs(parsed.query)
            if 'table' in query_params:
                table_values = query_params['table']
                if table_values:
                    return table_values[0]  # Return the first table value
            
            return None
        except Exception as e:
            logger.error(f"Error extracting replay ID from {url}: {e}")
            return None

    def _extract_map_from_table(self, html_content: str) -> Optional[str]:
        """
        Extract the selected map from table page HTML
        
        Args:
            html_content: HTML content of the table page
            
        Returns:
            str: Map name (e.g., "Tharsis") or None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the specific map element
            map_element = soup.find('span', id='gameoption_107_displayed_value')
            
            if map_element:
                map_name = map_element.get_text().strip()
                logger.info(f"Extracted map: {map_name}")
                return map_name
            else:
                logger.debug("Map element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting map from table HTML: {e}")
            return None

    def _extract_corporate_era_from_table(self, html_content: str) -> Optional[bool]:
        """
        Extract the Corporate Era setting from table page HTML
        
        Args:
            html_content: HTML content of the table page
            
        Returns:
            bool: True if Corporate Era is On, False if Off, None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the specific Corporate Era element
            corporate_era_element = soup.find('span', id='mob_gameoption_101_displayed_value')
            
            if corporate_era_element:
                corporate_era_text = corporate_era_element.get_text().strip()
                corporate_era_on = corporate_era_text.lower() == 'on'
                logger.info(f"Extracted Corporate Era: {corporate_era_text} -> {corporate_era_on}")
                return corporate_era_on
            else:
                logger.debug("Corporate Era element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Corporate Era from table HTML: {e}")
            return None

    def _extract_prelude_from_table(self, html_content: str) -> Optional[bool]:
        """
        Extract the Prelude setting from table page HTML
        
        Args:
            html_content: HTML content of the table page
            
        Returns:
            bool: True if Prelude is On, False if Off, None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the specific Prelude element
            prelude_element = soup.find('span', id='mob_gameoption_104_displayed_value')
            
            if prelude_element:
                prelude_text = prelude_element.get_text().strip()
                prelude_on = prelude_text.lower() == 'on'
                logger.info(f"Extracted Prelude: {prelude_text} -> {prelude_on}")
                return prelude_on
            else:
                logger.debug("Prelude element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Prelude from table HTML: {e}")
            return None

    def _extract_draft_from_table(self, html_content: str) -> Optional[bool]:
        """
        Extract the Draft setting from table page HTML
        
        Args:
            html_content: HTML content of the table page
            
        Returns:
            bool: True if Draft is Yes, False if No, None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the specific Draft element
            draft_element = soup.find('span', id='mob_gameoption_103_displayed_value')
            
            if draft_element:
                draft_text = draft_element.get_text().strip()
                draft_on = draft_text.lower() == 'yes'
                logger.info(f"Extracted Draft: {draft_text} -> {draft_on}")
                return draft_on
            else:
                logger.debug("Draft element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Draft from table HTML: {e}")
            return None

    def _extract_colonies_from_table(self, html_content: str) -> Optional[bool]:
        """
        Extract the Colonies setting from table page HTML
        
        Args:
            html_content: HTML content of the table page
            
        Returns:
            bool: True if Colonies is On, False if Off, None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the specific Colonies element
            colonies_element = soup.find('span', id='mob_gameoption_108_displayed_value')
            
            if colonies_element:
                colonies_text = colonies_element.get_text().strip()
                colonies_on = colonies_text.lower() == 'on'
                logger.info(f"Extracted Colonies: {colonies_text} -> {colonies_on}")
                return colonies_on
            else:
                logger.debug("Colonies element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Colonies from table HTML: {e}")
            return None

    def _extract_beginners_corporations_from_table(self, html_content: str) -> Optional[bool]:
        """
        Extract the Beginners Corporations setting from table page HTML
        
        Args:
            html_content: HTML content of the table page
            
        Returns:
            bool: True if Beginners Corporations is Yes, False if No, None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the specific Beginners Corporations element
            beginners_corps_element = soup.find('span', id='gameoption_100_displayed_value')
            
            if beginners_corps_element:
                beginners_corps_text = beginners_corps_element.get_text().strip()
                beginners_corps_on = beginners_corps_text.lower() == 'yes'
                logger.info(f"Extracted Beginners Corporations: {beginners_corps_text} -> {beginners_corps_on}")
                return beginners_corps_on
            else:
                logger.debug("Beginners Corporations element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Beginners Corporations from table HTML: {e}")
            return None

    def _extract_game_speed_from_table(self, html_content: str) -> Optional[str]:
        """
        Extract the Game Speed setting from table page HTML
        
        Args:
            html_content: HTML content of the table page
            
        Returns:
            str: Game speed text (e.g., "Real-time • Fast paced") or None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for the specific Game Speed element
            game_speed_element = soup.find('span', id='gameoption_200_displayed_value')
            
            if game_speed_element:
                game_speed_text = game_speed_element.get_text().strip()
                logger.info(f"Extracted Game Speed: {game_speed_text}")
                return game_speed_text
            else:
                logger.debug("Game Speed element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Game Speed from table HTML: {e}")
            return None
