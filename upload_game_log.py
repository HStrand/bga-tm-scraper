#!/usr/bin/env python3
"""
Upload Game Log Script for BGA TM Scraper

This script takes a JSON file containing a single parsed game and uploads it
via the store_game_log API method.

Usage:
    python upload_game_log.py <json_file_path> <user_email>

Arguments:
    json_file_path: Path to the JSON file containing the parsed game data
    user_email: BGA email of the user who scraped the game

Example:
    python upload_game_log.py parsed_game_12345.json user@example.com
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Import existing modules
from gui.api_client import APIClient
from gui.components.config_manager import ConfigManager


def setup_logging():
    """Setup basic logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load and parse JSON file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        dict: Parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    json_path = Path(file_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    if not json_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logging.info(f"Successfully loaded JSON file: {file_path}")
        return data
        
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in file {file_path}: {e}", e.doc, e.pos)


def validate_email(email: str) -> bool:
    """
    Basic email validation
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email appears valid
    """
    return "@" in email and "." in email.split("@")[-1]


def load_api_config() -> tuple[str, str]:
    """
    Load API configuration from config.json
    
    Returns:
        tuple: (api_key, base_url)
        
    Raises:
        ValueError: If API configuration is missing or invalid
    """
    try:
        config_manager = ConfigManager()
        api_settings = config_manager.get_section("api_settings")
        
        api_key = api_settings.get("api_key", "")
        base_url = api_settings.get("base_url", "")
        
        if not api_key:
            raise ValueError("API key not configured. Please set api_key in config.json")
        
        if not base_url:
            raise ValueError("API base URL not configured. Please set base_url in config.json")
        
        if api_key == "your_api_key_here":
            raise ValueError("API key is still set to default value. Please configure a real API key in config.json")
        
        logging.info("Successfully loaded API configuration")
        return api_key, base_url
        
    except Exception as e:
        raise ValueError(f"Failed to load API configuration: {e}")


def upload_game_log(game_data: Dict[str, Any], user_email: str, api_key: str, base_url: str) -> bool:
    """
    Upload game log data via API
    
    Args:
        game_data: Parsed game data dictionary
        user_email: BGA email of the user who scraped the game
        api_key: API key for authentication
        base_url: API base URL
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        # Create API client
        api_client = APIClient(api_key=api_key, base_url=base_url)
        
        # Test connection first
        logging.info("Testing API connection...")
        if not api_client.test_connection():
            logging.error("Failed to connect to API. Please check your API key and network connection.")
            return False
        
        logging.info("API connection successful")
        
        # Upload the game log
        logging.info(f"Uploading game log for user: {user_email}")
        success = api_client.store_game_log(game_data, user_email)
        
        if success:
            table_id = game_data.get('table_id', 'unknown')
            logging.info(f"Successfully uploaded game log for table {table_id}")
            return True
        else:
            logging.error("Failed to upload game log")
            return False
            
    except Exception as e:
        logging.error(f"Error during upload: {e}")
        return False


def main():
    """Main function"""
    setup_logging()
    
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python upload_game_log.py <json_file_path> <user_email>")
        print()
        print("Arguments:")
        print("  json_file_path: Path to the JSON file containing the parsed game data")
        print("  user_email: BGA email of the user who scraped the game")
        print()
        print("Example:")
        print("  python upload_game_log.py parsed_game_12345.json user@example.com")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    user_email = sys.argv[2]
    
    try:
        # Validate email format
        if not validate_email(user_email):
            logging.error(f"Invalid email format: {user_email}")
            sys.exit(1)
        
        # Load JSON file
        logging.info(f"Loading JSON file: {json_file_path}")
        game_data = load_json_file(json_file_path)
        
        # Load API configuration
        logging.info("Loading API configuration...")
        api_key, base_url = load_api_config()
        
        # Upload game log
        success = upload_game_log(game_data, user_email, api_key, base_url)
        
        if success:
            print("✅ Game log uploaded successfully!")
            sys.exit(0)
        else:
            print("❌ Failed to upload game log")
            sys.exit(1)
            
    except FileNotFoundError as e:
        logging.error(f"File error: {e}")
        print(f"❌ File not found: {e}")
        sys.exit(1)
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}")
        print(f"❌ Invalid JSON file: {e}")
        sys.exit(1)
        
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
        
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
