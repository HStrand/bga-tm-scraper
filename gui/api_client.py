"""
Shared API client for BGA TM Scraper GUI
Handles all API communication with the central registry
"""

import requests
import json
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class APIClient:
    """Client for communicating with the BGA TM Scraper API"""
    
    def __init__(self, api_key: str, base_url: str = "https://bga-tm-scraper-functions.azurewebsites.net/api"):
        """
        Initialize API client
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = 60  # Default timeout for requests
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None, params: Dict = None) -> Optional[Dict]:
        """
        Make a request to the API
        
        Args:
            endpoint: API endpoint name
            method: HTTP method (GET, POST)
            data: JSON data for POST requests
            params: Query parameters
            
        Returns:
            dict: Response data or None if failed
        """
        try:
            # Build URL with API key
            url = f"{self.base_url}/{endpoint}"
            
            # Add API key to params
            if params is None:
                params = {}
            params['code'] = self.api_key
            
            # Make request
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=self.timeout)
            elif method.upper() == "POST":
                if data is not None:
                    # Use explicit JSON serialization with ensure_ascii=False to preserve Unicode characters
                    headers = {'Content-Type': 'application/json; charset=utf-8'}
                    json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
                    response = requests.post(url, params=params, data=json_data, headers=headers, timeout=self.timeout)
                else:
                    response = requests.post(url, params=params, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle different response types
            if response.status_code == 204:  # No content
                return {}
            
            try:
                return response.json()
            except ValueError:
                # Response is not JSON, return text content
                return {"response": response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API request for {endpoint}: {e}")
            return None
    
    def get_next_player_to_index(self) -> Optional[str]:
        """
        Get the next player ID to scrape from the API
        
        Returns:
            str: Player ID or None if no more players available
        """
        try:
            response = self._make_request("GetNextPlayerToIndex")
            if response:
                player_id = response.get('playerId')
                if player_id:
                    logger.info(f"Got next player from API: {player_id}")
                    return str(player_id)
                else:
                    logger.info("No more players available from API")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error getting next player from API: {e}")
            return None
    
    def get_indexed_games_by_player(self, player_id: str) -> List[str]:
        """
        Get list of already indexed game table IDs for a player
        
        Args:
            player_id: Player ID to get indexed games for
            
        Returns:
            list: List of table IDs (strings) that are already indexed
        """
        try:
            params = {'playerId': player_id}
            response = self._make_request("GetIndexedGamesByPlayer", params=params)
            
            if response is not None:
                # Response should be a list of table IDs
                if isinstance(response, list):
                    table_ids = [str(tid) for tid in response]
                    logger.info(f"Found {len(table_ids)} indexed games for player {player_id}")
                    return table_ids
                else:
                    logger.warning(f"Unexpected response format for indexed games: {type(response)}")
                    return []
            else:
                logger.error(f"Failed to get indexed games for player {player_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting indexed games for player {player_id}: {e}")
            return []
    
    def update_single_game(self, game_data: Dict[str, Any]) -> bool:
        """
        POST a single game's data to the API
        
        Args:
            game_data: Dictionary containing the single game data to upload
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self._make_request("UpdateSingleGame", method="POST", data=game_data)
            
            if response is not None:
                logger.info(f"Successfully updated single game {game_data.get('table_id')} for player {game_data.get('player_perspective')}")
                return True
            else:
                logger.error(f"Failed to update single game {game_data.get('table_id')}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating single game: {e}")
            return False
    
    def store_game_log(self, game_log_data: Dict[str, Any], scraped_by_email: str = None) -> bool:
        """
        POST parsed game log data to the API
        
        Args:
            game_log_data: Dictionary containing the parsed game data
            scraped_by_email: BGA email of the user who scraped this game
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add scrapedBy parameter if email is provided
            params = {}
            if scraped_by_email:
                params['scrapedBy'] = scraped_by_email
            
            response = self._make_request("StoreGameLog", method="POST", data=game_log_data, params=params)
            
            if response is not None:
                table_id = game_log_data.get('table_id', 'unknown')
                logger.info(f"Successfully stored game log for table {table_id}")
                return True
            else:
                table_id = game_log_data.get('table_id', 'unknown')
                logger.error(f"Failed to store game log for table {table_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing game log: {e}")
            return False
    
    def update_players(self, players_data: List[Dict[str, Any]]) -> bool:
        """
        POST players data to the API
        
        Args:
            players_data: List of player dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self._make_request("UpdatePlayers", method="POST", data=players_data)
            
            if response is not None:
                logger.info(f"Successfully updated {len(players_data)} players")
                return True
            else:
                logger.error(f"Failed to update players data")
                return False
                
        except Exception as e:
            logger.error(f"Error updating players: {e}")
            return False
    
    def get_next_assignment(self, email: str, count: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get the next assignment for a user
        
        Args:
            email: User's BGA email
            count: Optional number of games to request (max 200, defaults to API default)
            
        Returns:
            dict: Assignment data or None if no assignment available
        """
        try:
            params = {'email': email}
            if count is not None:
                params['count'] = count
            response = self._make_request("GetNextAssignment", params=params)
            
            if response:
                logger.info(f"Got assignment from API for {email}" + (f" (count: {count})" if count else ""))
                return response
            else:
                logger.info(f"No assignment available for {email}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting assignment for {email}: {e}")
            return None
    
    def get_statistics(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a user
        
        Args:
            email: User's BGA email
            
        Returns:
            dict: Statistics data or None if failed
        """
        try:
            params = {'email': email}
            response = self._make_request("GetStatistics", params=params)
            
            if response:
                logger.info(f"Got statistics from API for {email}")
                return response
            else:
                logger.info(f"No statistics available for {email}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting statistics for {email}: {e}")
            return None
    
    def get_latest_zip_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the latest ZIP file from the API
        
        Returns:
            dict: File information with keys: success, fileName, sizeInBytes, sizeFormatted
                  or None if failed
        """
        try:
            logger.info("Getting latest ZIP file information from API")
            
            response = self._make_request("GetLatestZipSize")
            
            if response and response.get('success'):
                logger.info(f"Got file info: {response.get('fileName')} ({response.get('sizeFormatted')})")
                return response
            else:
                logger.error("API returned success=false for file info request")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error getting file info: {e}")
            return None
    
    def download_latest_zip(self, file_path: str, progress_callback=None, total_size=None) -> bool:
        """
        Download the latest ZIP file from the API
        
        Args:
            file_path: Local path where the file should be saved
            progress_callback: Optional callback function(downloaded_bytes, total_bytes)
            total_size: Optional total file size (if known from get_latest_zip_info)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Build URL with API key using the configured base URL and API key
            url = f"{self.base_url}/DownloadLatestZip"
            params = {'code': self.api_key}
            
            logger.info(f"Starting download from API to {file_path}")
            
            # Make request with streaming to handle large files
            response = requests.get(url, params=params, stream=True, timeout=300)  # 5 minute timeout
            response.raise_for_status()
            
            # If total_size wasn't provided, try to get it from response headers
            if total_size is None:
                content_length = response.headers.get('content-length')
                if content_length:
                    total_size = int(content_length)
                    logger.info(f"File size from headers: {total_size} bytes")
            else:
                logger.info(f"Using provided file size: {total_size} bytes")
            
            # Write the file in chunks with progress tracking
            downloaded_size = 0
            chunk_size = 8192
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(downloaded_size, total_size)
            
            logger.info(f"Successfully downloaded file to {file_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Download request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test the API connection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Try a simple endpoint that should always work
            response = self._make_request("GetNextPlayerToIndex")
            # Even if no players available, a successful response indicates connection works
            return response is not None
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
