# Terraforming Mars BGA Scraper

A Python CLI tool for scraping and parsing Terraforming Mars game replays from BoardGameArena.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation & Setup](#installation--setup)
- [Quick Start](#quick-start)
- [CLI Commands](#cli-commands)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [File Organization](#file-organization)
- [Usage Examples](#usage-examples)
- [License](#license)

## Features

- **CLI Interface**: Command-based interface for all operations
- **Web Scraping**: Automated data collection from both replay and table pages
- **Player Game History**: Automatically scrape all table IDs from a player's game history
- **Arena Mode Detection**: Automatically identifies and filters Arena mode games
- **ELO Data Extraction**: Arena points, game rank, and rating changes for each player
- **Comprehensive Parsing**: Complete game state reconstruction with move-by-move parsing
- **Game State Tracking**: Full game state tracking from start to finish including VP, resources, production and tags
- **Registry Management**: Tracks processed games to avoid duplicates
- **Smart Filtering**: Skip players with completed discovery automatically

## Requirements

### System Requirements
- **Python 3.7+**
- **Google Chrome browser** (latest version recommended)
- **Windows/macOS/Linux** (tested on Windows 11)

**Note**: ChromeDriver is now installed automatically! No manual setup required.

### Important Limitations
- **BGA Daily Replay Limit**: BoardGameArena has a daily limit on replay access that resets after 24 hours. This limits how many replays you can scrape per day.

### Python Dependencies
- `requests>=2.31.0` - HTTP requests
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=4.9.0` - XML/HTML processing
- `selenium>=4.15.0` - Browser automation
- `psutil>=5.9.0` - System process management
- `webdriver-manager>=4.0.0` - Automatic ChromeDriver management

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd bga-tm-scraper
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Settings
```bash
cp config.example.py config.py
```

Edit `config.py` and update:
- `BGA_EMAIL` and `BGA_PASSWORD`: Your BoardGameArena credentials
- Other settings as needed (see [Configuration](#configuration))

**Note**: ChromeDriver will be downloaded automatically when you first run the scraper!

### 4. Verify Setup
```bash
# Check if everything is working
python main.py status
```

## Quick Start

### 1. Update Player Registry
```bash
# Get top 100 Arena players
python main.py update-players --count 100
```

### 2. Check Status
```bash
# See what's in the registry
python main.py status --detailed
```

### 3. Start Scraping
```bash
# Complete workflow for all players (tables + replays + parsing)
python main.py scrape-complete --all

# Or use API-based table scraping (requires API_KEY)
python main.py scrape-tables
```

### 4. Parse Games
```bash
# Parse games that have been scraped
python main.py parse
```

## CLI Commands

The CLI provides six main commands for different operations:

### `scrape-tables` - Scrape table HTMLs only
Scrapes table pages to identify Arena mode games and extract basic information.

> **⚠️ IMPORTANT**: This command now integrates with a cloud API and cannot be used for local-only scraping. It requires API access and uploads data to the cloud service. Use `scrape-complete` or `scrape-replays` for local-only operations.

```bash
# API mode - gets players from cloud API (requires API_KEY)
python main.py scrape-tables

# Manual mode - specific players (still uploads to API)
python main.py scrape-tables 12345678 87654321 11223344
```

**Options:**
- `--retry-failed`: Include previously failed games

**Note**: This command no longer supports `--all` or `--update-players` flags as it operates in API mode.

### `scrape-complete` - Full workflow (tables + replays + parsing)
Performs the complete workflow: scrapes tables, scrapes replays for Arena games, and parses them.

```bash
# Complete workflow for all players
python main.py scrape-complete --all --update-players

# Complete workflow for specific players
python main.py scrape-complete 12345678 87654321

# Retry failed games for specific players
python main.py scrape-complete 12345678 --retry-failed
```

**Options:**
- `--all, -a`: Process all players from the registry
- `--update-players`: Update player registry before processing
- `--retry-failed`: Include previously failed games

### `scrape-replays` - Scrape replays and parse (requires table HTMLs)
Scrapes replay pages and parses games that already have table HTML scraped.

```bash
# Process all games that need replay scraping
python main.py scrape-replays

# Process specific games (using composite keys)
python main.py scrape-replays 123456789:12345678 987654321:87654321
```

**Composite Key Format:** `table_id:player_perspective`
- Example: `123456789:12345678` means table ID 123456789 from player 12345678's perspective

### `parse` - Parse games only (requires both HTMLs)
Parses games that have both table and replay HTML files already scraped.

```bash
# Parse all games ready for parsing
python main.py parse

# Parse specific games
python main.py parse 123456789:12345678 987654321:87654321

# Reparse all games (including already parsed ones)
python main.py parse --reparse

# Reparse specific games
python main.py parse --reparse 123456789:12345678 987654321:87654321
```

**Options:**
- `--reparse`: Reparse already parsed games (overwrite existing JSON files)

### `update-players` - Update player registry
Updates the player registry with the latest Arena leaderboard data.

```bash
# Update with default number of players (from config)
python main.py update-players

# Update with specific number of top players
python main.py update-players --count 200
```

### `status` - Show registry status
Displays statistics about the current state of the games registry.

```bash
# Basic status
python main.py status

# Detailed status with breakdowns
python main.py status --detailed
```

## How It Works

### 1. Player Registry Management
- Fetches top Arena players from BoardGameArena leaderboards
- Maintains a registry of players to track (`data/registry/players.csv`)

### 2. Table Scraping
- Visits each player's game history page
- Automatically loads all games by clicking "See more" until all games have been loaded
- Extracts table IDs and basic game information
- Identifies Arena mode games using ELO data presence
- Stores raw HTML in `data/raw/{player_id}/table_{table_id}.html`
- Scrapes game version number used in the game from the game review page

### 3. Replay Scraping
- Scrapes detailed replay pages
- Uses browser automation to handle dynamic content
- Extracts complete game logs and player actions
- Stores replay HTML in `data/raw/{player_id}/replay_{table_id}.html`
- **Note**: BGA enforces a daily replay limit that resets after 24 hours, which restricts the number of replays that can be scraped per day

### 4. Game Parsing
- Processes both table and replay HTML files
- Reconstructs complete game state move-by-move
- Extracts player data, cards, resources, terraforming parameters etc.
- Combines ELO data from table pages with game data
- Exports structured JSON files to `data/parsed/{player_id}/game_{table_id}.json`

### 5. Registry Tracking
- Maintains `data/registry/games.csv` to track processing status
- Prevents duplicate processing
- Tracks scraping and parsing timestamps
- Handles version management for replay URLs

### 6. Smart Filtering
- Automatically skips players with completed discovery
- Checks for `complete_summary.json` files with `discovery_completed: true`
- Provides filtering statistics during processing

## Configuration

Key settings in `config.py`:

### Paths and Browser
```python
# ChromeDriver is now managed automatically!
# Only set CHROMEDRIVER_PATH if you want to use a specific driver
CHROMEDRIVER_PATH = None  # Uses webdriver-manager (recommended)
CHROME_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe'  # Optional
```

### BGA Credentials
```python
BGA_EMAIL = "your_email@example.com"
BGA_PASSWORD = "your_password"
```

### Scraping Settings
```python
REQUEST_DELAY = 2  # Seconds between requests
TOP_N_PLAYERS = 1000  # Number of players to fetch
```

### Speed Profiles
Choose from predefined profiles or customize:
```python
SPEED_PROFILE = "NORMAL"  # Options: "FAST", "NORMAL", "SLOW", "CUSTOM"
```

## File Organization

```
bga-tm-scraper/
├── main.py                    # CLI entry point
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── bga_tm_scraper/           # Core modules
│   ├── scraper.py            # Web scraping logic
│   ├── parser.py             # Game parsing logic
│   ├── games_registry.py     # Registry management
│   ├── players_registry.py   # Player management
│   └── bga_session.py        # BGA session handling
├── data/
│   ├── raw/                  # Raw HTML files
│   │   └── {player_id}/
│   │       ├── table_{table_id}.html
│   │       └── replay_{table_id}.html
│   ├── parsed/               # Processed JSON files
│   │   └── {player_id}/
│   │       ├── game_{table_id}.json
│   │       └── complete_summary.json
│   └── registry/             # Registry files
│       ├── games.csv         # Games tracking
│       └── players.csv       # Players list
└── scraper.log              # Application logs
```

## Usage Examples

### Initial Setup Workflow
```bash
# 1. Update player registry with top 100 players
python main.py update-players --count 100

# 2. Check what's in the registry
python main.py status --detailed

# 3. Use API-based table scraping (requires API_KEY)
python main.py scrape-tables

# 4. Check progress
python main.py status

# 5. Run complete workflow for new data
python main.py scrape-complete --all
```

### Targeted Processing
```bash
# Process specific players
python main.py scrape-complete 12345678 87654321

# Process specific games that failed
python main.py scrape-replays 123456789:12345678 987654321:87654321

# Retry failed games for a player
python main.py scrape-complete 12345678 --retry-failed

# Reparse specific games
python main.py parse --reparse 123456789:12345678
```

### Sample Output Structure

The parser generates comprehensive JSON (sample excerpt):

```json
{
  "replay_id": "689196352",
  "player_perspective": "86296239",
  "game_date": "2025-06-20",
  "game_duration": "00:30",
  "winner": "StrandedKnight",
  "generations": 10,
  "players": {
    "86296239": {
      "corporation": "Tharsis Republic",
      "final_vp": 83,
      "final_tr": 39,
      "elo_data": {
        "arena_points": 1788,
        "arena_points_change": 34,
        "game_rank": 469,
        "game_rank_change": 16
      }
    }
  },
  "moves": [
    {
      "move_number": 5,
      "timestamp": "8:28:15",
      "player_id": "86296239",
      "player_name": "StrandedKnight",
      "action_type": "play_card",
      "description": "StrandedKnight plays card Aquifer Turbines | StrandedKnight increases  by 2 (immediate effect of Aquifer Turbines) | StrandedKnight pays 3",
      "card_played": "Aquifer Turbines",
      "game_state": {
        "move_number": 5,
        "generation": 1,
        "temperature": -30,
        "oxygen": 0,
        "oceans": 0,
        "player_vp": {
          "86296239": {
            "total": 20,
            "total_details": {
              "tr": 20,
              "awards": 0,
              "milestones": 0,
              "cities": 0,
              "greeneries": 0,
              "cards": 0
            },
            "details": {}
          }
      },
      "milestones": {},
        "awards": {},
        "player_trackers": {
          "86296239": {
            "Plant": 0,
            "Heat Production": 0,
            "Titanium Production": 0,
            "Energy Production": 2,
            "Steel": 0,
            "Count of City tags": 0,
            "Count of Space tags": 0,
            "Count of Building tags": 0,
            "Count of Power tags": 1,
            "Count of Microbe tags": 0,
            "Hand Counter": 8,
            "Count of Science tags": 0,
            "Player Area Counter": 3,
            "Count of Plant tags": 0,
            "Titanium": 0,
            "Count of Animal tags": 0,
            "Count of Earth tags": 0,
            "M€ Production": 0,
            "Count of Jovian tags": 0,
            "Steel Production": 0,
            "Plant Production": 0,
            "Count of played Events cards": 0,
            "Count of Wild tags": 0,
            "M€": 16,
            "Heat": 0,
            "Energy": 0,
            "Microbe": 0
          }
    }
  "parameter_progression": [
    {
      "move_number": 5,
      "generation": 1,
      "temperature": -30,
      "oxygen": 0,
      "oceans": 0
    }
  ]
}
```

## Troubleshooting

### ChromeDriver Issues

**Automatic Installation (Default)**
ChromeDriver is now installed automatically! If you encounter issues:

1. **First Run**: ChromeDriver downloads automatically on first use
2. **Version Mismatch**: webdriver-manager automatically handles Chrome version compatibility
3. **Network Issues**: Check your internet connection and proxy settings
4. **Permission Issues**: Ensure your antivirus isn't blocking the download

**Manual Installation (If Needed)**
If you prefer manual ChromeDriver management or encounter issues with automatic installation:

1. Check your Chrome version: Go to `chrome://version/`
2. Download matching ChromeDriver from https://chromedriver.chromium.org/
3. Extract to a folder (e.g., `C:\Code\chromedriver-win64\`)
4. Update your `config.py`:
   ```python
   CHROMEDRIVER_PATH = r'C:\path\to\chromedriver.exe'
   USE_WEBDRIVER_MANAGER = False  # Disable automatic management
   ```
   
### Logging

- All operations are logged to `scraper.log`
- Use `--detailed` flag with status command for more information
- Check registry files for processing history

## License

This project is for educational and research purposes. Please respect BoardGameArena's terms of service and use responsibly.
