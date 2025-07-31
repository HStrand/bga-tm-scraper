"""
BGA Session Management
Combines session-based authentication with Selenium browser automation
Eliminates the need for manual login by transferring authenticated session cookies
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import os
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


class BGASession:
    """
    BGA session manager that combines requests.Session authentication
    with Selenium WebDriver automation, eliminating manual login requirements
    """
    
    BASE_URL = 'https://boardgamearena.com'
    LOGIN_URL = '/account/account/login.html'
    
    def __init__(self, email: str, password: str, chromedriver_path: str, chrome_path: str=None, headless: bool = False):
        """
        Initialize session manager
        
        Args:
            email: BGA account email
            password: BGA account password
            chromedriver_path: Path to ChromeDriver executable
            headless: Whether to run Chrome in headless mode
        """
        self.email = email
        self.password = password
        self.chromedriver_path = chromedriver_path
        self.chrome_path = chrome_path
        self.headless = headless
        
        # Session-based components
        self.session = requests.Session()
        self.request_token: Optional[str] = None
        self.is_session_logged_in = False
        
        # Browser-based components
        self.driver: Optional[webdriver.Chrome] = None
        self.is_browser_logged_in = False
        
        # Combined status
        self.is_fully_authenticated = False
    
    def login(self) -> bool:
        """
        Perform complete authentication: session login + browser cookie transfer
        
        Returns:
            bool: True if both session and browser authentication successful
        """
        logger.info("Starting authentication process...")
        
        # Step 1: Authenticate with session-based approach
        if not self._login_session():
            logger.error("Session-based login failed")
            return False
        
        # Step 2: Start browser if not already started
        if not self.driver:
            if not self._start_browser():
                logger.error("Failed to start browser")
                return False
        
        # Step 3: Transfer session cookies to browser
        if not self._transfer_cookies_to_browser():
            logger.error("Failed to transfer cookies to browser")
            return False
        
        # Step 4: Verify browser authentication
        if not self._verify_browser_authentication():
            logger.error("Browser authentication verification failed")
            return False
        
        self.is_fully_authenticated = True
        logger.info("✅ Authentication completed successfully!")
        return True
    
    def _login_session(self, max_retries: int = 3, retry_delay: int = 2) -> bool:
        """
        Perform session-based login using requests with retry logic
        
        Args:
            max_retries: Maximum number of retries for token extraction and login
            retry_delay: Delay between retries in seconds
            
        Returns:
            bool: True if session login successful
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Performing session-based login (attempt {attempt + 1}/{max_retries})...")
                
                # First, get a page to extract request token with retries
                self.request_token = self._extract_request_token_with_retry(max_retries=max_retries, retry_delay=retry_delay)
                if not self.request_token:
                    logger.error("Failed to extract request token after multiple retries")
                    return False
                
                logger.debug(f"Extracted request token: {self.request_token[:10]}...")
                
                # Set headers for authenticated requests
                self.session.headers.update({
                    'X-Request-Token': self.request_token,
                    'X-Requested-With': 'XMLHttpRequest',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                # Perform login
                logger.info("Submitting login credentials...")
                login_data = {
                    'email': self.email,
                    'password': self.password,
                    'rememberme': 'off',
                    'redirect': 'join',
                    'form_id': 'loginform',
                    'request_token': self.request_token
                }
                
                login_resp = self.session.post(f'{self.BASE_URL}{self.LOGIN_URL}', data=login_data, timeout=15)
                login_resp.raise_for_status()

                # Verify login by checking for authentication indicators
                if self._verify_session_authentication():
                    self.is_session_logged_in = True
                    logger.info("✅ Session-based login successful")
                    return True
                else:
                    logger.warning(f"Session login verification failed on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Session login failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error("Max retries reached for session login")
                    return False
            except Exception as e:
                logger.error(f"An unexpected error occurred during session login: {e}")
                return False
        
        logger.error("Session login failed after all retries")
        return False
    
    def _extract_request_token_with_retry(self, max_retries: int = 3, retry_delay: int = 2) -> Optional[str]:
        """
        Extract request token from a BGA page with retry logic
        
        Args:
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            
        Returns:
            str: Request token, or None if failed
        """
        for attempt in range(max_retries):
            try:
                logger.debug(f"Fetching initial page to extract request token (attempt {attempt + 1}/{max_retries})...")
                
                # Use a page that is less likely to be rate-limited
                resp = self.session.get(f'{self.BASE_URL}/gamelist', timeout=15)
                resp.raise_for_status()
                
                # Extract request token from JavaScript
                token = self._extract_request_token(resp.content)
                if token:
                    return token
                
                logger.warning(f"Failed to extract request token on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page for token extraction on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        return None

    def _extract_request_token(self, html_content: bytes) -> Optional[str]:
        """Extract request token from HTML content"""
        try:
            # Use regex for faster extraction without full parsing
            # Pattern looks for: requestToken: '...'
            token_pattern = re.compile(rb"requestToken:\s*'([^']+)'")
            match = token_pattern.search(html_content)
            
            if match:
                token = match.group(1).decode('utf-8')
                logger.debug(f"Extracted token with regex: {token[:10]}...")
                return token
            
            # Fallback to BeautifulSoup if regex fails
            logger.debug("Regex for token failed, falling back to BeautifulSoup")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for script_tag in soup.find_all('script'):
                if script_tag.string:
                    script_content = script_tag.string
                    if 'requestToken: ' in script_content:
                        # More robust extraction from script content
                        token_match = re.search(r"requestToken:\s*'([^']+)'", script_content)
                        if token_match:
                            token = token_match.group(1)
                            logger.debug(f"Extracted token with BeautifulSoup: {token[:10]}...")
                            return token
            
            logger.warning("Request token not found in HTML content")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting request token: {e}")
            return None
    
    def _verify_session_authentication(self) -> bool:
        """Verify that session-based authentication was successful"""
        try:
            # Test authentication by accessing a protected page
            test_resp = self.session.get(f'{self.BASE_URL}/account')
            test_resp.raise_for_status()
            
            # Check for login indicators in response
            page_content = test_resp.text.lower()
            
            # If we see login forms, we're not authenticated
            if 'login' in page_content and 'password' in page_content:
                return False
            
            # If we see account/profile indicators, we're authenticated
            if any(indicator in page_content for indicator in ['logout', 'my account', 'profile']):
                return True
            
            # Additional check: try to access player stats
            stats_resp = self.session.get(f'{self.BASE_URL}/gamestats', params={'player': "689196352"})
            if stats_resp.status_code == 200 and 'must be logged' not in stats_resp.text.lower():
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying session authentication: {e}")
            return False
    
    def _setup_chromedriver_service(self) -> Service:
        """
        Setup ChromeDriver service with smart detection
        
        Returns:
            Service: Configured ChromeDriver service
        """
        # Priority order:
        # 1. Manual path (if configured and exists)
        # 2. webdriver-manager (with built-in caching)
        
        if (self.chromedriver_path and 
            self.chromedriver_path != "None" and 
            os.path.exists(self.chromedriver_path)):
            
            logger.info(f"Using manual ChromeDriver path: {self.chromedriver_path}")
            return Service(self.chromedriver_path)
        
        else:
            logger.info("Using webdriver-manager for ChromeDriver")
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                
                # This call is fast if driver is cached, only downloads if needed
                driver_path = ChromeDriverManager().install()
                logger.info(f"ChromeDriver ready at: {driver_path}")
                return Service(driver_path)
                
            except ImportError:
                logger.error("webdriver-manager not installed. Please install it with: pip install webdriver-manager")
                raise RuntimeError("webdriver-manager not available and no manual ChromeDriver path provided")
            except Exception as e:
                logger.error(f"webdriver-manager failed: {e}")
                raise RuntimeError(f"ChromeDriver setup failed: {e}")

    def _start_browser(self) -> bool:
        """Start Chrome browser with appropriate options"""
        try:
            logger.info("Starting Chrome browser...")
            
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            # Add useful Chrome options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Set user agent to match session requests
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            if self.chrome_path:
                # If a custom Chrome path is provided, set it
                chrome_options.binary_location = self.chrome_path
            
            # Setup ChromeDriver service with smart detection
            service = self._setup_chromedriver_service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute script to hide automation indicators
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Chrome browser started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False
    
    def _transfer_cookies_to_browser(self) -> bool:
        """Transfer authenticated session cookies to Selenium browser"""
        try:
            logger.info("Transferring session cookies to browser...")
            
            # First navigate to BGA domain so we can set cookies
            self.driver.get(self.BASE_URL)
            time.sleep(2)
            
            # Get cookies from requests session
            session_cookies = self.session.cookies
            
            if not session_cookies:
                logger.warning("No cookies found in session")
                return False
            
            # Transfer each cookie to browser
            cookies_transferred = 0
            for cookie in session_cookies:
                try:
                    cookie_dict = {
                        'name': cookie.name,
                        'value': cookie.value,
                        'domain': cookie.domain if cookie.domain else '.boardgamearena.com',
                        'path': cookie.path if cookie.path else '/',
                    }
                    
                    # Add optional cookie attributes if they exist
                    if cookie.secure:
                        cookie_dict['secure'] = True
                    
                    self.driver.add_cookie(cookie_dict)
                    cookies_transferred += 1
                    logger.debug(f"Transferred cookie: {cookie.name}")
                    
                except Exception as e:
                    logger.debug(f"Failed to transfer cookie {cookie.name}: {e}")
                    continue
            
            logger.info(f"✅ Transferred {cookies_transferred} cookies to browser")
            
            # Refresh page to apply cookies
            self.driver.refresh()
            time.sleep(2)
            
            return cookies_transferred > 0
            
        except Exception as e:
            logger.error(f"Error transferring cookies to browser: {e}")
            return False
    
    def _verify_browser_authentication(self) -> bool:
        """Verify that browser has been successfully authenticated"""
        try:
            logger.info("Verifying browser authentication...")
            
            # Navigate to a page that requires authentication
            self.driver.get(f'{self.BASE_URL}/account')
            time.sleep(3)
            
            # Check page source for authentication indicators
            page_source = self.driver.page_source.lower()
            
            # If we see login forms, authentication failed
            if 'must be logged' in page_source or ('login' in page_source and 'password' in page_source):
                logger.warning("Browser shows login required - authentication failed")
                return False
            
            # Look for authenticated user indicators
            authenticated_indicators = ['logout', 'my account', 'player_name', 'profile']
            if any(indicator in page_source for indicator in authenticated_indicators):
                logger.info("✅ Browser authentication verified")
                self.is_browser_logged_in = True
                return True
            
            # Additional test: try to access game stats
            self.driver.get(f'{self.BASE_URL}/gamestats?player=689196352')
            time.sleep(2)
            
            page_source = self.driver.page_source.lower()
            if 'must be logged' not in page_source and 'fatal error' not in page_source:
                logger.info("✅ Browser authentication verified via game stats")
                self.is_browser_logged_in = True
                return True
            
            logger.warning("Browser authentication verification failed")
            return False
            
        except Exception as e:
            logger.error(f"Error verifying browser authentication: {e}")
            return False
    
    def refresh_authentication(self) -> bool:
        """
        Refresh authentication if session expires
        
        Returns:
            bool: True if refresh successful
        """
        logger.info("Refreshing authentication...")
        
        # Reset authentication status
        self.is_session_logged_in = False
        self.is_browser_logged_in = False
        self.is_fully_authenticated = False
        
        # Perform fresh login
        return self.login()
    
    def check_authentication_status(self) -> Dict[str, bool]:
        """
        Check current authentication status
        
        Returns:
            dict: Status of session, browser, and overall authentication
        """
        status = {
            'session_authenticated': self.is_session_logged_in,
            'browser_authenticated': self.is_browser_logged_in,
            'fully_authenticated': self.is_fully_authenticated
        }
        
        # Quick verification if needed
        if self.is_fully_authenticated:
            try:
                # Quick check of browser status
                if self.driver:
                    current_url = self.driver.current_url
                    if 'boardgamearena.com' in current_url:
                        page_source = self.driver.page_source.lower()
                        if 'must be logged' in page_source:
                            status['browser_authenticated'] = False
                            status['fully_authenticated'] = False
                            self.is_browser_logged_in = False
                            self.is_fully_authenticated = False
            except:
                pass
        
        return status
    
    def get_session(self) -> requests.Session:
        """
        Get the authenticated requests session
        
        Returns:
            requests.Session: Authenticated session for API calls
        """
        if not self.is_session_logged_in:
            raise RuntimeError("Session not authenticated. Call login() first.")
        return self.session
    
    def get_driver(self) -> webdriver.Chrome:
        """
        Get the authenticated Selenium WebDriver
        
        Returns:
            webdriver.Chrome: Authenticated browser driver
        """
        if not self.is_browser_logged_in:
            raise RuntimeError("Browser not authenticated. Call login() first.")
        return self.driver
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Make authenticated GET request (compatibility method for LeaderboardScraper)
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            requests.Response: Response object
        """
        if not self.is_session_logged_in:
            raise RuntimeError("Session not authenticated. Call login() first.")
        return self.session.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """
        Make authenticated POST request (compatibility method for LeaderboardScraper)
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            requests.Response: Response object
        """
        if not self.is_session_logged_in:
            raise RuntimeError("Session not authenticated. Call login() first.")
        return self.session.post(url, **kwargs)
    
    @property
    def is_logged_in(self) -> bool:
        """
        Check if session is logged in (compatibility property for LeaderboardScraper)
        
        Returns:
            bool: True if session is authenticated
        """
        return self.is_session_logged_in
    
    def close_browser(self):
        """Close the browser if it's open"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except:
                pass
            finally:
                self.driver = None
                self.is_browser_logged_in = False
                self.is_fully_authenticated = False
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.close_browser()
