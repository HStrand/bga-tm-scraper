# BoardGameArena Configuration Template
# Copy this file to config.py and update with your values

# URL templates for constructing BGA URLs
TABLE_URL_TEMPLATE = "https://boardgamearena.com/table?table={table_id}"
REPLAY_URL_TEMPLATE = "https://boardgamearena.com/archive/replay/{version_id}/?table={table_id}&player={player_id}&comments={player_id}"


# Request settings
REQUEST_DELAY = 2  # Seconds between requests
TIMEOUT = 30  # Request timeout in seconds
MAX_RETRIES = 3  # Maximum retry attempts

# Data storage paths
RAW_DATA_DIR = 'data/raw'
PROCESSED_DATA_DIR = 'data/processed'
PARSED_DATA_DIR = 'data/parsed'
REGISTRY_DATA_DIR = 'data/registry'

# Chrome settings
CHROME_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe'  # Update this path
CHROMEDRIVER_PATH = None  # Optional: Set to specific path if you want to use manual ChromeDriver, otherwise webdriver-manager will handle it automatically

# ChromeDriver Management
USE_WEBDRIVER_MANAGER = True  # Set to False if you prefer manual ChromeDriver management
WEBDRIVER_MANAGER_CACHE_VALID_RANGE = 7  # Days to consider cached driver valid (optional)

# BGA Login Credentials
BGA_EMAIL = "your_email@example.com"
BGA_PASSWORD = "your_password"

# Leaderboard settings
TERRAFORMING_MARS_GAME_ID = 1924
TOP_N_PLAYERS = 1000 # Number of players to fetch from leaderboard

# Speed settings for scraping
# Choose one of the predefined speed profiles or create a custom one

# Speed profile options: "FAST", "NORMAL", "SLOW", "CUSTOM"
SPEED_PROFILE = "NORMAL"

# Predefined speed profiles
SPEED_PROFILES = {
    "FAST": {
        "page_load_delay": 2,
        "click_delay": 0.3,
        "gamereview_delay": 1.5,
        "element_wait_timeout": 5
    },
    "NORMAL": {
        "page_load_delay": 3,
        "click_delay": 0.5,
        "gamereview_delay": 2.5,
        "element_wait_timeout": 8
    },
    "SLOW": {
        "page_load_delay": 5,
        "click_delay": 1.0,
        "gamereview_delay": 4.0,
        "element_wait_timeout": 12
    },
    "CUSTOM": {
        "page_load_delay": 3,
        "click_delay": 0.5,
        "gamereview_delay": 2.5,
        "element_wait_timeout": 8
    }
}

# Current speed settings (automatically set based on SPEED_PROFILE)
CURRENT_SPEED = SPEED_PROFILES[SPEED_PROFILE]

# Speed setting descriptions:
# - page_load_delay: Time to wait after navigating to a page (seconds)
# - click_delay: Time to wait between clicks when auto-clicking "See more" (seconds)
# - gamereview_delay: Time to wait for gamereview page to load (seconds)
# - element_wait_timeout: Maximum time to wait for elements to appear (seconds)

# API Configuration
API_KEY = "your_api_key_here"  # Update with your actual API key
