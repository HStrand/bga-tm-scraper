"""
Configuration Manager for BGA TM Scraper GUI
Handles loading, saving, and managing GUI-specific configuration
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import base64


class ConfigManager:
    """Manages GUI configuration with JSON storage"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config_data = {}
        self.load_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration structure"""
        return {
            "bga_credentials": {
                "email": "",
                "password": "",  # Will be base64 encoded for basic obfuscation
                "display_name": ""
            },
            "browser_settings": {
                "chrome_path": "",
                "chromedriver_path": "",
                "headless": True
            },
            "api_settings": {
                "api_key": "",
                "base_url": "https://bga-tm-scraper-functions.azurewebsites.net/api",
                "timeout": 30
            },
            "scraping_settings": {
                "request_delay": 1.0,
                "max_retries": 3,
                "speed_profile": "FAST",
                "replay_limit_hit_at": None
            },
            "email_settings": {
                "enabled": False,
                "sender_email": "",
                "app_password": "",
                "recipient_email": "",
                "notify_on_completion": True,
                "notify_on_error": True,
                "notify_on_daily_limit": True
            },
            "ui_settings": {
                "window_size": [900, 700],
                "last_tab": 0,
                "theme": "default"
            },
            "data_paths": {
                "raw_data_dir": "data/raw",
                "parsed_data_dir": "data/parsed",
                "registry_data_dir": "data/registry"
            }
        }
    
    def load_config(self):
        """Load configuration from file or create default"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                default_config = self.get_default_config()
                self.config_data = self._merge_configs(default_config, self.config_data)
            else:
                self.config_data = self.get_default_config()
                self.save_config()
        
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config_data = self.get_default_config()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"Error saving config: {e}")
            raise
    
    def get_section(self, section_name: str) -> Dict[str, Any]:
        """Get a configuration section"""
        return self.config_data.get(section_name, {})
    
    def update_section(self, section_name: str, section_data: Dict[str, Any]):
        """Update a configuration section"""
        if section_name not in self.config_data:
            self.config_data[section_name] = {}
        
        self.config_data[section_name].update(section_data)
    
    def get_value(self, section: str, key: str, default=None):
        """Get a specific configuration value"""
        return self.config_data.get(section, {}).get(key, default)
    
    def set_value(self, section: str, key: str, value: Any):
        """Set a specific configuration value"""
        if section not in self.config_data:
            self.config_data[section] = {}
        
        self.config_data[section][key] = value
    
    def encode_password(self, password: str) -> str:
        """Encode password for basic obfuscation (not secure encryption)"""
        if not password:
            return ""
        return base64.b64encode(password.encode('utf-8')).decode('utf-8')
    
    def decode_password(self, encoded_password: str) -> str:
        """Decode password from base64"""
        if not encoded_password:
            return ""
        try:
            return base64.b64decode(encoded_password.encode('utf-8')).decode('utf-8')
        except:
            return ""  # Return empty string if decoding fails
    
    def set_bga_credentials(self, email: str, password: str, display_name: str):
        """Set BGA credentials with password encoding"""
        self.update_section("bga_credentials", {
            "email": email,
            "password": self.encode_password(password),
            "display_name": display_name
        })
    
    def get_bga_credentials(self) -> tuple[str, str, str]:
        """Get BGA credentials with password decoding"""
        creds = self.get_section("bga_credentials")
        email = creds.get("email", "")
        encoded_password = creds.get("password", "")
        password = self.decode_password(encoded_password)
        display_name = creds.get("display_name", "")
        return email, password, display_name
    
    def validate_config(self) -> Dict[str, list]:
        """Validate current configuration and return issues"""
        issues = {
            "errors": [],
            "warnings": []
        }
        
        # Check BGA credentials
        email, password, _ = self.get_bga_credentials()
        if not email:
            issues["errors"].append("BGA email is required")
        if not password:
            issues["errors"].append("BGA password is required")
        
        # Check API key
        api_key = self.get_value("api_settings", "api_key", "")
        if not api_key or api_key == "your_api_key_here":
            issues["warnings"].append("API key not configured")
        
        # Check Chrome path
        chrome_path = self.get_value("browser_settings", "chrome_path", "")
        if chrome_path and not Path(chrome_path).exists():
            issues["warnings"].append("Chrome path does not exist")
        
        return issues
    
    def export_config(self, file_path: str):
        """Export configuration to a file"""
        export_data = self.config_data.copy()
        
        # Don't export sensitive data in plain text
        if "bga_credentials" in export_data:
            export_data["bga_credentials"]["password"] = "[HIDDEN]"
        if "email_settings" in export_data:
            export_data["email_settings"]["app_password"] = "[HIDDEN]"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def import_config(self, file_path: str):
        """Import configuration from a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # Merge imported data with current config
            self.config_data = self._merge_configs(self.config_data, imported_data)
            
            # Save the updated config
            self.save_config()
            
        except Exception as e:
            raise Exception(f"Failed to import config: {e}")
    
    def import_from_cli_config(self, cli_config_path: str):
        """Import settings from the CLI config.py file"""
        try:
            # This would parse the CLI config.py and extract relevant settings
            # For now, this is a placeholder
            pass
        except Exception as e:
            raise Exception(f"Failed to import CLI config: {e}")
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge user config with default config"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_speed_profiles(self) -> Dict[str, Dict[str, float]]:
        """Get available speed profiles for scraping"""
        return {
            "FAST": {
                "page_load_delay": 2.0,
                "click_delay": 0.3,
                "gamereview_delay": 1.5,
                "element_wait_timeout": 5.0
            },
            "NORMAL": {
                "page_load_delay": 3.0,
                "click_delay": 0.5,
                "gamereview_delay": 2.5,
                "element_wait_timeout": 8.0
            },
            "SLOW": {
                "page_load_delay": 5.0,
                "click_delay": 1.0,
                "gamereview_delay": 4.0,
                "element_wait_timeout": 12.0
            }
        }
    
    def get_current_speed_settings(self) -> Dict[str, float]:
        """Get current speed settings based on selected profile"""
        profile_name = self.get_value("scraping_settings", "speed_profile", "NORMAL")
        profiles = self.get_speed_profiles()
        return profiles.get(profile_name, profiles["NORMAL"])

    def set_replay_limit_hit_at(self, timestamp: Optional[str]):
        """Set the timestamp when the daily replay limit was hit"""
        self.set_value("scraping_settings", "replay_limit_hit_at", timestamp)
        self.save_config()

    def get_replay_limit_hit_at(self) -> Optional[str]:
        """Get the timestamp when the daily replay limit was hit"""
        return self.get_value("scraping_settings", "replay_limit_hit_at", None)
    
    def generate_assignment_id(self, assignment_data: Dict[str, Any]) -> str:
        """Generate a unique ID for an assignment"""
        import hashlib
        
        # Create a string representation of key assignment data
        assignment_type = assignment_data.get("type", "unknown")
        details = assignment_data.get("details", {})
        
        if assignment_type == "replayscraping":
            # For replay assignments, use player perspective + game count + first few table IDs
            player_id = details.get("player_perspective_id", "unknown")
            game_count = details.get("game_count", 0)
            games = details.get("games", [])
            first_games = [str(g.get("tableId", "")) for g in games[:3]]  # First 3 games as identifier
            id_string = f"{assignment_type}_{player_id}_{game_count}_{'-'.join(first_games)}"
        elif assignment_type == "indexing":
            # For indexing assignments, use player ID
            player_id = details.get("player_id", "unknown")
            id_string = f"{assignment_type}_{player_id}"
        else:
            # Fallback for other assignment types
            id_string = f"{assignment_type}_{str(details)}"
        
        # Create hash for consistent ID
        return hashlib.md5(id_string.encode()).hexdigest()[:16]
    
    def save_assignment_progress(self, assignment_id: str, progress_data: Dict[str, Any]):
        """Save progress data for an assignment"""
        if "assignment_progress" not in self.config_data:
            self.config_data["assignment_progress"] = {}
        
        self.config_data["assignment_progress"][assignment_id] = progress_data
        self.save_config()
    
    def load_assignment_progress(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """Load progress data for an assignment"""
        return self.config_data.get("assignment_progress", {}).get(assignment_id)
    
    def update_game_completion(self, assignment_id: str, table_id: str, success: bool):
        """Update completion status for a specific game"""
        from datetime import datetime
        
        progress = self.load_assignment_progress(assignment_id)
        if not progress:
            # Initialize progress if it doesn't exist
            progress = {
                "completed_games": [],
                "failed_games": [],
                "last_processed_index": -1,
                "counters": {
                    "total_items": 0,
                    "completed_items": 0,
                    "successful_items": 0,
                    "failed_items": 0
                },
                "timestamps": {
                    "started_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
        
        # Update game completion
        table_id_str = str(table_id)
        if success:
            if table_id_str not in progress["completed_games"]:
                progress["completed_games"].append(table_id_str)
                progress["counters"]["successful_items"] += 1
            # Remove from failed if it was there
            if table_id_str in progress["failed_games"]:
                progress["failed_games"].remove(table_id_str)
                progress["counters"]["failed_items"] -= 1
        else:
            if table_id_str not in progress["failed_games"]:
                progress["failed_games"].append(table_id_str)
                progress["counters"]["failed_items"] += 1
            # Remove from completed if it was there
            if table_id_str in progress["completed_games"]:
                progress["completed_games"].remove(table_id_str)
                progress["counters"]["successful_items"] -= 1
        
        # Update counters
        progress["counters"]["completed_items"] = len(progress["completed_games"]) + len(progress["failed_games"])
        progress["timestamps"]["last_updated"] = datetime.now().isoformat()
        
        # Save updated progress
        self.save_assignment_progress(assignment_id, progress)
    
    def clear_assignment_progress(self, assignment_id: str):
        """Clear progress data for an assignment"""
        if "assignment_progress" in self.config_data:
            self.config_data["assignment_progress"].pop(assignment_id, None)
            self.save_config()
    
    def get_all_assignment_progress(self) -> Dict[str, Dict[str, Any]]:
        """Get all assignment progress data"""
        return self.config_data.get("assignment_progress", {})
    
    def cleanup_old_progress(self, days_old: int = 7):
        """Clean up progress data older than specified days"""
        from datetime import datetime, timedelta
        
        if "assignment_progress" not in self.config_data:
            return
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        progress_data = self.config_data["assignment_progress"]
        
        # Find old progress entries
        old_assignments = []
        for assignment_id, progress in progress_data.items():
            try:
                last_updated = datetime.fromisoformat(progress.get("timestamps", {}).get("last_updated", ""))
                if last_updated < cutoff_date:
                    old_assignments.append(assignment_id)
            except (ValueError, TypeError):
                # If we can't parse the date, consider it old
                old_assignments.append(assignment_id)
        
        # Remove old progress entries
        for assignment_id in old_assignments:
            progress_data.pop(assignment_id, None)
        
        if old_assignments:
            self.save_config()
            print(f"Cleaned up {len(old_assignments)} old progress entries")
