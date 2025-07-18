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
                "password": ""  # Will be base64 encoded for basic obfuscation
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
                "speed_profile": "FAST"
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
    
    def set_bga_credentials(self, email: str, password: str):
        """Set BGA credentials with password encoding"""
        self.update_section("bga_credentials", {
            "email": email,
            "password": self.encode_password(password)
        })
    
    def get_bga_credentials(self) -> tuple[str, str]:
        """Get BGA credentials with password decoding"""
        creds = self.get_section("bga_credentials")
        email = creds.get("email", "")
        encoded_password = creds.get("password", "")
        password = self.decode_password(encoded_password)
        return email, password
    
    def validate_config(self) -> Dict[str, list]:
        """Validate current configuration and return issues"""
        issues = {
            "errors": [],
            "warnings": []
        }
        
        # Check BGA credentials
        email, password = self.get_bga_credentials()
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
