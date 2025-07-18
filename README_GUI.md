# BGA TM Scraper - Desktop GUI Application

A user-friendly desktop interface for the Terraforming Mars scraper, built with Python and Tkinter.

## Features

### 🔧 Settings Management
- **BGA Account Configuration**: Email and password with show/hide functionality
- **Browser Settings**: Chrome and ChromeDriver path configuration with file browsers
- **API Configuration**: API key and endpoint settings with validation
- **Scraping Settings**: Request delays, retry limits, speed profiles, and filters
- **Email Notifications**: Optional email alerts for completion, errors, and daily limits
- **Real-time Validation**: Visual indicators for configuration status

### 📋 Assignment System
- **Get Assignments**: Retrieve scraping tasks from the central registry
- **Assignment Types**: 
  - Index Games: Scrape game metadata for specific players
  - Collect Logs: Download detailed replay data for indexed games
- **Assignment Details**: View task requirements and instructions
- **Accept/Decline**: Choose assignments that fit your preferences

### 🚀 Scraping Operations
- **Progress Tracking**: Real-time progress bars and statistics
- **Live Updates**: Activity log with timestamped operations
- **Background Processing**: Non-blocking scraping with cancellation support
- **Success Metrics**: Track successful vs failed operations
- **Time Estimation**: Elapsed time and completion estimates

### 📊 Statistics Dashboard
- **Personal Stats**: Your contribution metrics and recent activity
- **Global Stats**: Community-wide statistics and leaderboards
- **Visual Charts**: Simple bar and line charts for performance tracking
- **Top Contributors**: See who's contributing the most to the project

### 💾 Data Download
- **Dataset Options**: Complete dataset, games only, or logs only
- **Format Selection**: JSON (structured) or CSV (spreadsheet-friendly)
- **Progress Monitoring**: Download progress with speed and ETA
- **File Management**: Automatic file naming and folder opening

## Installation

### Prerequisites
- Python 3.7 or higher
- tkinter (usually included with Python)

### Setup
1. **Clone or download** the scraper project
2. **Install dependencies**:
   ```bash
   pip install -r requirements_gui.txt
   ```
3. **Run the GUI**:
   ```bash
   python gui_main.py
   ```

## First Time Setup

1. **Launch the application** - it will open to the Settings tab
2. **Configure BGA credentials** - enter your BoardGameArena email and password
3. **Set API key** - enter your API key for the central registry
4. **Adjust settings** - configure Chrome path, scraping speed, etc. as needed
5. **Save settings** - click "Save Settings" to store your configuration

## Usage Workflow

### Basic Workflow
1. **Settings** → Configure your credentials and preferences
2. **Get Assignment** → Request a scraping task from the registry
3. **Start Scraping** → Execute the assignment with progress tracking
4. **Statistics** → View your contributions and community stats
5. **Download Data** → Get the scraped data for analysis

### Assignment Types

#### Index Games
- Scrapes game metadata for a specific player
- Identifies Arena mode games
- Extracts basic game information and ELO data
- Faster processing, good for building the game index

#### Collect Logs
- Downloads detailed replay data for indexed games
- Processes move-by-move game logs
- Extracts complete game state information
- Slower processing, provides rich data for analysis

## Configuration

The GUI uses its own configuration file (`gui_config.json`) separate from the CLI scraper. This includes:

- **BGA Credentials**: Stored with basic encoding (not secure encryption)
- **Browser Settings**: Chrome and ChromeDriver paths
- **API Settings**: Registry endpoint and authentication
- **Scraping Preferences**: Speed profiles, filters, retry settings
- **UI Preferences**: Window size, last selected tab

## Mock Implementation

Currently, the GUI includes mock implementations for:
- **Assignment retrieval** (generates sample assignments)
- **Scraping operations** (simulates progress with realistic timing)
- **Statistics data** (shows sample personal and global metrics)
- **Data downloads** (creates placeholder files)

These will be replaced with real API calls and scraper integration in future versions.

## File Structure

```
gui/
├── main_window.py          # Main application window
├── components/
│   └── config_manager.py   # Configuration management
└── tabs/
    ├── settings_tab.py     # Settings configuration
    ├── assignment_tab.py   # Assignment management
    ├── scraping_tab.py     # Scraping operations
    ├── statistics_tab.py   # Statistics display
    └── download_tab.py     # Data download

gui_main.py                 # Application entry point
gui_config.json            # GUI configuration file (auto-created)
requirements_gui.txt        # Python dependencies
```

## Development Status

### ✅ Completed (Phase 1)
- Basic application structure and tabbed interface
- Complete settings management with validation
- Mock assignment system with realistic data
- Progress tracking for scraping operations
- Statistics dashboard with charts
- Data download interface with progress monitoring

### 🔄 Next Steps (Phase 2)
- Integration with existing scraper modules
- Real API endpoint connections
- Actual file processing and uploads
- Enhanced error handling and recovery
- PyInstaller packaging for distribution

### 🎯 Future Enhancements (Phase 3+)
- Advanced filtering options for downloads
- Scheduling and automation features
- Enhanced charts and visualizations
- Plugin system for custom analysis
- Multi-language support

## Packaging for Distribution

To create a standalone executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --windowed --name "BGA_TM_Scraper" gui_main.py

# The executable will be in the dist/ folder
```

## Troubleshooting

### Common Issues

**GUI doesn't start**
- Ensure Python 3.7+ is installed
- Check that tkinter is available: `python -c "import tkinter"`

**Settings not saving**
- Check file permissions in the application directory
- Ensure the directory is writable

**Mock data not realistic**
- This is expected - mock implementations will be replaced with real functionality

### Getting Help

- Check the main project README.md for CLI scraper documentation
- Review the configuration examples in the Settings tab
- Use the "Test Connection" buttons to verify your setup

## Contributing

This GUI application is part of the larger BGA TM Scraper project. Contributions are welcome for:
- UI/UX improvements
- Additional chart types and visualizations
- Integration with the existing scraper modules
- Cross-platform compatibility testing
- Documentation and examples

## License

Same as the main project - for educational and research purposes. Please respect BoardGameArena's terms of service.
