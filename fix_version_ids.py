#!/usr/bin/env python3
"""
Script to fix version IDs in games.csv for Arena mode games that haven't been scraped/parsed yet.

This script:
1. Finds games where IsArenaMode=1 AND ScrapedAt is empty AND ParsedAt is empty
2. Uses the current scraper logic to extract correct version IDs
3. Updates the CSV with the corrected version IDs
4. Creates backups and provides detailed logging
"""

import os
import sys
import csv
import argparse
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bga_tm_scraper.scraper import TMScraper
import config

# Configure logging with UTF-8 encoding to handle Unicode characters
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_version_ids.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VersionFixer:
    """Class to handle version ID correction for games in the registry"""
    
    def __init__(self, csv_path: str = "data/registry/games.csv", dry_run: bool = False):
        """
        Initialize the version fixer
        
        Args:
            csv_path: Path to the games CSV file
            dry_run: If True, don't actually modify the CSV
        """
        self.csv_path = csv_path
        self.dry_run = dry_run
        self.scraper: Optional[TMScraper] = None
        self.backup_path: Optional[str] = None
        
        # Statistics
        self.stats = {
            'total_games': 0,
            'games_processed': 0,
            'versions_updated': 0,
            'no_changes': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Track changes for verification
        self.changes_made: List[Dict] = []
    
    def load_games_needing_correction(self) -> List[Dict]:
        """
        Load games from CSV that need version correction
        
        Returns:
            List of game dictionaries that need correction
        """
        games_needing_correction = []
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Check if this game needs correction
                    if (row.get('IsArenaMode') == '1' and 
                        not row.get('ScrapedAt') and 
                        not row.get('ParsedAt')):
                        games_needing_correction.append(row)
            
            logger.info(f"Found {len(games_needing_correction)} games needing version correction")
            return games_needing_correction
            
        except Exception as e:
            logger.error(f"Error loading games from CSV: {e}")
            return []
    
    def create_backup(self) -> bool:
        """
        Create a backup of the original CSV file
        
        Returns:
            True if backup created successfully, False otherwise
        """
        try:
            # Create backup directory if it doesn't exist
            backup_dir = "backup"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            backup_filename = f"games_{timestamp}.csv"
            self.backup_path = os.path.join(backup_dir, backup_filename)
            
            # Copy the original file
            shutil.copy2(self.csv_path, self.backup_path)
            
            logger.info(f"Created backup: {self.backup_path}")
            print(f"📁 Created backup: {self.backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            print(f"❌ Error creating backup: {e}")
            return False
    
    def initialize_scraper(self) -> bool:
        """
        Initialize the scraper with authentication
        
        Returns:
            True if scraper initialized successfully, False otherwise
        """
        try:
            print("🔐 Initializing scraper with authentication...")
            
            # Initialize scraper with credentials from config
            self.scraper = TMScraper(
                chromedriver_path=config.CHROMEDRIVER_PATH,
                chrome_path=config.CHROME_PATH,
                request_delay=config.REQUEST_DELAY,
                headless=True,  # Use headless mode for batch processing
                email=config.BGA_EMAIL,
                password=config.BGA_PASSWORD
            )
            
            # Start browser and login
            if not self.scraper.start_browser_and_login():
                logger.error("Failed to initialize scraper and login")
                print("❌ Failed to initialize scraper and login")
                return False
            
            print("✅ Scraper initialized and authenticated successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing scraper: {e}")
            print(f"❌ Error initializing scraper: {e}")
            return False
    
    def extract_correct_version(self, table_id: str) -> Optional[str]:
        """
        Extract the correct version ID for a table using current scraper logic
        
        Args:
            table_id: BGA table ID
            
        Returns:
            Correct version ID or None if extraction failed
        """
        try:
            if not self.scraper:
                logger.error("Scraper not initialized")
                return None
            
            # Use the scraper's extract_version_from_gamereview method
            version = self.scraper.extract_version_from_gamereview(table_id)
            
            if version:
                logger.info(f"Successfully extracted version {version} for table {table_id}")
                return version
            else:
                logger.warning(f"Could not extract version for table {table_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting version for table {table_id}: {e}")
            return None
    
    def update_single_game_in_csv(self, table_id: str, new_version: str) -> bool:
        """
        Update a single game's version in the CSV file immediately
        
        Args:
            table_id: BGA table ID to update
            new_version: New version ID to set
            
        Returns:
            True if update successful, False otherwise
        """
        if self.dry_run:
            print(f"  🔍 DRY RUN: Would update table {table_id} to version {new_version}")
            return True
        
        try:
            # Read all rows from the CSV
            all_rows = []
            fieldnames = []
            updated = False
            
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                all_rows = list(reader)
            
            # Find and update the specific row
            for row in all_rows:
                if row.get('TableId') == table_id:
                    old_version = row.get('Version', '')
                    if old_version != new_version:
                        row['Version'] = new_version
                        updated = True
                        logger.info(f"Updated table {table_id}: {old_version} -> {new_version}")
                        print(f"  💾 CSV updated: {old_version} → {new_version}")
                    break
            
            if updated:
                # Write the updated CSV back
                with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_rows)
                
                return True
            else:
                print(f"  ⚠️  No update needed for table {table_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating CSV for table {table_id}: {e}")
            print(f"  ❌ Error updating CSV: {e}")
            return False

    def update_csv_with_corrections(self, corrections: List[Dict]) -> bool:
        """
        Update the CSV file with the corrected version IDs (batch mode - legacy)
        
        Args:
            corrections: List of correction dictionaries
            
        Returns:
            True if update successful, False otherwise
        """
        if self.dry_run:
            print("🔍 DRY RUN: Would update CSV with the following corrections:")
            for correction in corrections:
                print(f"  Table {correction['table_id']}: {correction['old_version']} → {correction['new_version']}")
            return True
        
        try:
            # Read all rows from the original CSV
            all_rows = []
            fieldnames = []
            
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                all_rows = list(reader)
            
            # Create a lookup dictionary for corrections
            corrections_lookup = {c['table_id']: c['new_version'] for c in corrections}
            
            # Update the rows with corrections
            updated_count = 0
            for row in all_rows:
                table_id = row.get('TableId')
                if table_id in corrections_lookup:
                    old_version = row.get('Version', '')
                    new_version = corrections_lookup[table_id]
                    if old_version != new_version:
                        row['Version'] = new_version
                        updated_count += 1
                        logger.info(f"Updated table {table_id}: {old_version} -> {new_version}")
            
            # Write the updated CSV
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
            
            logger.info(f"Successfully updated CSV with {updated_count} corrections")
            print(f"✅ Updated CSV with {updated_count} corrections")
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSV: {e}")
            print(f"❌ Error updating CSV: {e}")
            return False
    
    def process_games(self, games: List[Dict], limit: Optional[int] = None, 
                     delay: float = 1.0, resume: bool = False) -> List[Dict]:
        """
        Process games to extract correct version IDs and update CSV immediately
        
        Args:
            games: List of game dictionaries to process
            limit: Maximum number of games to process (None for all)
            delay: Delay between requests in seconds
            resume: If True, skip games that already have correct versions
            
        Returns:
            List of correction dictionaries
        """
        corrections = []
        games_to_process = games[:limit] if limit else games
        
        self.stats['total_games'] = len(games_to_process)
        
        print(f"🚀 Starting version correction for {len(games_to_process)} games...")
        print("💾 CSV will be updated immediately after each successful extraction")
        
        for i, game in enumerate(games_to_process, 1):
            table_id = game.get('TableId')
            old_version = game.get('Version', '')
            
            print(f"\nProcessing game {i}/{len(games_to_process)}: Table {table_id}")
            print(f"  Current version: {old_version}")
            
            try:
                # Extract correct version
                new_version = self.extract_correct_version(table_id)
                
                if new_version:
                    if old_version != new_version:
                        print(f"  New version: {new_version} ✅")
                        
                        # Update CSV immediately
                        if self.update_single_game_in_csv(table_id, new_version):
                            corrections.append({
                                'table_id': table_id,
                                'old_version': old_version,
                                'new_version': new_version
                            })
                            self.stats['versions_updated'] += 1
                            
                            # Track change for verification
                            self.changes_made.append({
                                'table_id': table_id,
                                'old_version': old_version,
                                'new_version': new_version,
                                'timestamp': datetime.now().isoformat()
                            })
                        else:
                            print(f"  ❌ Failed to update CSV for table {table_id}")
                            self.stats['errors'] += 1
                    else:
                        print(f"  New version: {new_version} (no change)")
                        self.stats['no_changes'] += 1
                else:
                    print(f"  ❌ Could not extract version")
                    self.stats['errors'] += 1
                
                self.stats['games_processed'] += 1
                
                # Delay between requests (except for the last one)
                if i < len(games_to_process):
                    print(f"  ⏱️  Waiting {delay} seconds...")
                    time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error processing game {table_id}: {e}")
                print(f"  ❌ Error: {e}")
                self.stats['errors'] += 1
        
        return corrections
    
    def print_summary(self):
        """Print a summary of the correction process"""
        print("\n" + "="*60)
        print("📊 CORRECTION SUMMARY")
        print("="*60)
        print(f"Games found needing correction: {self.stats['total_games']}")
        print(f"Games processed: {self.stats['games_processed']}")
        print(f"Versions updated: {self.stats['versions_updated']}")
        print(f"No changes needed: {self.stats['no_changes']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Skipped: {self.stats['skipped']}")
        
        if self.backup_path:
            print(f"Backup created: {self.backup_path}")
        
        if self.changes_made:
            print(f"\nChanges made:")
            for change in self.changes_made[:10]:  # Show first 10 changes
                print(f"  {change['table_id']}: {change['old_version']} → {change['new_version']}")
            if len(self.changes_made) > 10:
                print(f"  ... and {len(self.changes_made) - 10} more changes")
        
        print("="*60)
    
    def save_changes_log(self):
        """Save a detailed log of all changes made"""
        if not self.changes_made:
            return
        
        try:
            log_filename = f"version_corrections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(log_filename, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['table_id', 'old_version', 'new_version', 'timestamp']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.changes_made)
            
            print(f"📝 Changes log saved: {log_filename}")
            logger.info(f"Changes log saved: {log_filename}")
            
        except Exception as e:
            logger.error(f"Error saving changes log: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.scraper:
            try:
                self.scraper.close_browser()
                print("🔒 Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

def main():
    """Main function to run the version correction script"""
    parser = argparse.ArgumentParser(description="Fix version IDs in games.csv for Arena mode games")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without modifying CSV')
    parser.add_argument('--limit', type=int, 
                       help='Process only first N games')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Seconds between requests (default: 1.0)')
    parser.add_argument('--csv-path', default='data/registry/games.csv',
                       help='Path to games CSV file')
    parser.add_argument('--resume', action='store_true',
                       help='Skip games that already have correct versions')
    
    args = parser.parse_args()
    
    print("🔧 BGA Terraforming Mars Version ID Fixer")
    print("="*50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Initialize the fixer
    fixer = VersionFixer(csv_path=args.csv_path, dry_run=args.dry_run)
    
    try:
        # Load games needing correction
        games = fixer.load_games_needing_correction()
        
        if not games:
            print("✅ No games found needing version correction!")
            return
        
        print(f"🔍 Found {len(games)} games needing version correction")
        
        if args.limit:
            print(f"📊 Processing limit: {args.limit} games")
        
        # Create backup (unless dry run)
        if not args.dry_run:
            if not fixer.create_backup():
                print("❌ Failed to create backup - aborting")
                return
        
        # Initialize scraper
        if not fixer.initialize_scraper():
            print("❌ Failed to initialize scraper - aborting")
            return
        
        # Process games (CSV is updated immediately after each game)
        corrections = fixer.process_games(
            games=games,
            limit=args.limit,
            delay=args.delay,
            resume=args.resume
        )
        
        # No need for batch update since we update immediately
        if corrections:
            print("✅ All corrections have been applied to CSV!")
        else:
            print("ℹ️  No corrections needed")
        
        # Save changes log
        fixer.save_changes_log()
        
        # Print summary
        fixer.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
    finally:
        # Cleanup
        fixer.cleanup()

if __name__ == "__main__":
    main()
