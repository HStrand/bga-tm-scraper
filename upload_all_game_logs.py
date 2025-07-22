#!/usr/bin/env python3
"""
Batch Upload Game Logs Script for BGA TM Scraper

This script loops through all JSON files in the data/parsed directory
and uploads them via the store_game_log API method.

Usage:
    python upload_all_game_logs.py <user_email> [options]

Arguments:
    user_email: BGA email of the user who scraped the games

Options:
    --dry-run: Show what files would be uploaded without actually uploading
    --continue-on-error: Continue processing even if some uploads fail
    --max-files: Maximum number of files to process (for testing)

Examples:
    python upload_all_game_logs.py user@example.com
    python upload_all_game_logs.py user@example.com --dry-run
    python upload_all_game_logs.py user@example.com --continue-on-error --max-files 10
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import time

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


def find_json_files(parsed_dir: Path) -> List[Path]:
    """
    Recursively find all JSON files in the parsed directory
    
    Args:
        parsed_dir: Path to the data/parsed directory
        
    Returns:
        List[Path]: List of JSON file paths
    """
    json_files = []
    
    if not parsed_dir.exists():
        logging.error(f"Parsed directory does not exist: {parsed_dir}")
        return json_files
    
    # Recursively find all .json files
    for json_file in parsed_dir.rglob("*.json"):
        if json_file.is_file():
            json_files.append(json_file)
    
    logging.info(f"Found {len(json_files)} JSON files in {parsed_dir}")
    return sorted(json_files)


def load_json_file(file_path: Path) -> Tuple[Dict[str, Any], bool]:
    """
    Load and parse JSON file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Tuple[Dict[str, Any], bool]: (parsed_data, success)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data, True
        
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in file {file_path}: {e}")
        return {}, False
    except Exception as e:
        logging.error(f"Error loading file {file_path}: {e}")
        return {}, False


def validate_email(email: str) -> bool:
    """
    Basic email validation
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email appears valid
    """
    return "@" in email and "." in email.split("@")[-1]


def load_api_config() -> Tuple[str, str, bool]:
    """
    Load API configuration from config.json
    
    Returns:
        Tuple[str, str, bool]: (api_key, base_url, success)
    """
    try:
        config_manager = ConfigManager()
        api_settings = config_manager.get_section("api_settings")
        
        api_key = api_settings.get("api_key", "")
        base_url = api_settings.get("base_url", "")
        
        if not api_key:
            logging.error("API key not configured. Please set api_key in config.json")
            return "", "", False
        
        if not base_url:
            logging.error("API base URL not configured. Please set base_url in config.json")
            return "", "", False
        
        if api_key == "your_api_key_here":
            logging.error("API key is still set to default value. Please configure a real API key in config.json")
            return "", "", False
        
        logging.info("Successfully loaded API configuration")
        return api_key, base_url, True
        
    except Exception as e:
        logging.error(f"Failed to load API configuration: {e}")
        return "", "", False


def upload_game_log(api_client: APIClient, game_data: Dict[str, Any], user_email: str, file_path: Path) -> bool:
    """
    Upload a single game log via API
    
    Args:
        api_client: Configured API client
        game_data: Parsed game data dictionary
        user_email: BGA email of the user who scraped the game
        file_path: Path to the source file (for logging)
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        success = api_client.store_game_log(game_data, user_email)
        
        if success:
            table_id = game_data.get('table_id', 'unknown')
            logging.info(f"✅ Successfully uploaded {file_path.name} (table {table_id})")
            return True
        else:
            logging.error(f"❌ Failed to upload {file_path.name}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Error uploading {file_path.name}: {e}")
        return False


def print_summary(total_files: int, successful_uploads: int, failed_uploads: int, skipped_files: int, elapsed_time: float):
    """Print upload summary"""
    print("\n" + "="*60)
    print("UPLOAD SUMMARY")
    print("="*60)
    print(f"Total files found:     {total_files}")
    print(f"Successful uploads:    {successful_uploads}")
    print(f"Failed uploads:        {failed_uploads}")
    print(f"Skipped files:         {skipped_files}")
    print(f"Success rate:          {(successful_uploads/max(1, total_files-skipped_files))*100:.1f}%")
    print(f"Total time:            {elapsed_time:.1f} seconds")
    if successful_uploads > 0:
        print(f"Average time per file: {elapsed_time/successful_uploads:.2f} seconds")
    print("="*60)


def main():
    """Main function"""
    setup_logging()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Batch upload all JSON files from data/parsed directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upload_all_game_logs.py user@example.com
  python upload_all_game_logs.py user@example.com --dry-run
  python upload_all_game_logs.py user@example.com --continue-on-error --max-files 10
        """
    )
    
    parser.add_argument("user_email", help="BGA email of the user who scraped the games")
    parser.add_argument("--dry-run", action="store_true", help="Show what files would be uploaded without actually uploading")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue processing even if some uploads fail")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process (for testing)")
    parser.add_argument("--parsed-dir", default="data/parsed", help="Path to parsed data directory (default: data/parsed)")
    
    args = parser.parse_args()
    
    try:
        # Validate email format
        if not validate_email(args.user_email):
            logging.error(f"Invalid email format: {args.user_email}")
            sys.exit(1)
        
        # Find all JSON files
        parsed_dir = Path(args.parsed_dir)
        json_files = find_json_files(parsed_dir)
        
        if not json_files:
            logging.error(f"No JSON files found in {parsed_dir}")
            sys.exit(1)
        
        # Limit files if max_files is specified
        if args.max_files:
            json_files = json_files[:args.max_files]
            logging.info(f"Limited to first {len(json_files)} files due to --max-files option")
        
        # Load API configuration (unless dry run)
        api_client = None
        if not args.dry_run:
            api_key, base_url, config_success = load_api_config()
            if not config_success:
                sys.exit(1)
            
            # Create API client and test connection
            api_client = APIClient(api_key=api_key, base_url=base_url)
            logging.info("Testing API connection...")
            if not api_client.test_connection():
                logging.error("Failed to connect to API. Please check your API key and network connection.")
                sys.exit(1)
            logging.info("API connection successful")
        
        # Process files
        start_time = time.time()
        successful_uploads = 0
        failed_uploads = 0
        skipped_files = 0
        
        print(f"\n{'='*60}")
        if args.dry_run:
            print(f"DRY RUN - Processing {len(json_files)} files")
        else:
            print(f"UPLOADING {len(json_files)} files")
        print(f"{'='*60}")
        
        for i, json_file in enumerate(json_files, 1):
            print(f"\n[{i}/{len(json_files)}] Processing: {json_file.relative_to(parsed_dir)}")
            
            # Load JSON file
            game_data, load_success = load_json_file(json_file)
            if not load_success:
                logging.warning(f"Skipping {json_file.name} due to loading error")
                skipped_files += 1
                if not args.continue_on_error:
                    logging.error("Stopping due to error (use --continue-on-error to continue)")
                    break
                continue
            
            if args.dry_run:
                table_id = game_data.get('table_id', 'unknown')
                print(f"  Would upload table {table_id}")
                successful_uploads += 1
            else:
                # Upload the file
                upload_success = upload_game_log(api_client, game_data, args.user_email, json_file)
                if upload_success:
                    successful_uploads += 1
                else:
                    failed_uploads += 1
                    if not args.continue_on_error:
                        logging.error("Stopping due to upload error (use --continue-on-error to continue)")
                        break
            
            # Small delay to avoid overwhelming the API
            if not args.dry_run:
                time.sleep(0.1)
        
        # Print summary
        elapsed_time = time.time() - start_time
        print_summary(len(json_files), successful_uploads, failed_uploads, skipped_files, elapsed_time)
        
        # Exit with appropriate code
        if args.dry_run:
            print("\n✅ Dry run completed successfully!")
            sys.exit(0)
        elif failed_uploads == 0 and skipped_files == 0:
            print("\n✅ All files uploaded successfully!")
            sys.exit(0)
        elif successful_uploads > 0:
            print(f"\n⚠️  Partial success: {successful_uploads} uploaded, {failed_uploads} failed, {skipped_files} skipped")
            sys.exit(1)
        else:
            print("\n❌ No files were uploaded successfully")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Upload interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
