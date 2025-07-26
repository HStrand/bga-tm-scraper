"""
Terraforming Mars game log parser for BoardGameArena replays
Comprehensive parser that extracts all game data into a structured format
"""
import re
import json
import os
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from bs4 import BeautifulSoup, Tag
import logging

logger = logging.getLogger(__name__)

@dataclass
class EloData:
    """Represents ELO information for a player"""
    arena_points: Optional[int] = None
    arena_points_change: Optional[int] = None
    game_rank: Optional[int] = None
    game_rank_change: Optional[int] = None
    player_name: Optional[str] = None
    player_id: Optional[str] = None
    position: Optional[int] = None

@dataclass
class GameMetadata:
    """Represents metadata from table HTML or assignment for replay scraping"""
    played_at: Optional[str] = None  # ISO timestamp when game was played
    map: Optional[str] = None
    prelude_on: Optional[bool] = None
    colonies_on: Optional[bool] = None
    corporate_era_on: Optional[bool] = None
    draft_on: Optional[bool] = None
    beginners_corporations_on: Optional[bool] = None
    game_speed: Optional[str] = None
    game_mode: Optional[str] = None
    version_id: Optional[str] = None
    players: Optional[Dict[str, EloData]] = None  # player_id -> EloData

@dataclass
class GameState:
    """Represents the game state at a specific point in time"""
    move_number: int
    generation: int
    temperature: int
    oxygen: int
    oceans: int
    player_vp: Dict[str, Dict[str, Any]]  # player_id -> VP breakdown
    milestones: Dict[str, Dict[str, Any]]  # milestone_name -> details
    awards: Dict[str, Dict[str, Any]]  # award_name -> details
    player_trackers: Dict[str, Dict[str, int]] = None  # player_id -> tracker_name -> value
    
    def __post_init__(self):
        if self.player_vp is None:
            self.player_vp = {}
        if self.milestones is None:
            self.milestones = {}
        if self.awards is None:
            self.awards = {}
        if self.player_trackers is None:
            self.player_trackers = {}

@dataclass
class Move:
    """Represents a single move in the game"""
    move_number: int
    timestamp: str
    player_id: str
    player_name: str
    action_type: str
    description: str
    
    # Detailed action data
    card_played: Optional[str] = None
    tile_placed: Optional[str] = None
    tile_location: Optional[str] = None
    
    # Game state after this move
    game_state: Optional[GameState] = None

@dataclass
class Player:
    """Represents a player in the game"""
    player_id: str
    player_name: str
    corporation: str
    final_vp: int
    final_tr: int
    vp_breakdown: Dict[str, Any]
    cards_played: List[str]
    milestones_claimed: List[str]
    awards_funded: List[str]
    elo_data: Optional[EloData] = None

@dataclass
class GameData:
    """Complete game data structure"""
    # Game metadata
    replay_id: str
    player_perspective: str
    game_date: str
    game_duration: str
    winner: str
    generations: int
    
    # New assignment metadata fields (top-level)
    map: Optional[str] = None
    prelude_on: Optional[bool] = None
    colonies_on: Optional[bool] = None
    corporate_era_on: Optional[bool] = None
    draft_on: Optional[bool] = None
    beginners_corporations_on: Optional[bool] = None
    game_speed: Optional[str] = None
    
    # Players
    players: Dict[str, Player] = None  # player_id -> Player
    
    # All moves with game states
    moves: List[Move] = None

    # Analysis metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.players is None:
            self.players = {}
        if self.moves is None:
            self.moves = []
        if self.metadata is None:
            self.metadata = {}

class Parser:
    """Comprehensive Terraforming Mars game log parser for BoardGameArena replays"""
    
    def __init__(self):
        pass
    
    def parse_table_metadata(self, table_html: str) -> GameMetadata:
        """Extract all metadata from table HTML including game mode, map, settings, and ELO data"""
        logger.info("Parsing table metadata from HTML")
        
        soup = BeautifulSoup(table_html, 'html.parser')
        
        # Extract game mode
        game_mode = self._extract_game_mode_from_table(table_html)
        
        # Extract map
        map_name = self._extract_map_from_table(table_html)
        
        # Extract game settings
        corporate_era_on = self._extract_corporate_era_from_table(table_html)
        prelude_on = self._extract_prelude_from_table(table_html)
        draft_on = self._extract_draft_from_table(table_html)
        colonies_on = self._extract_colonies_from_table(table_html)
        beginners_corporations_on = self._extract_beginners_corporations_from_table(table_html)
        game_speed = self._extract_game_speed_from_table(table_html)
        
        # Extract ELO data and convert to Dict[str, EloData] with string keys
        elo_data_dict = self.parse_elo_data(table_html)
        players_dict = {}
        for player_name, elo_data in elo_data_dict.items():
            # Ensure player_id is string
            player_id = str(elo_data.player_id) if elo_data.player_id else ""
            if player_id:
                players_dict[player_id] = elo_data
        
        metadata = GameMetadata(
            map=map_name,
            prelude_on=prelude_on,
            colonies_on=colonies_on,
            corporate_era_on=corporate_era_on,
            draft_on=draft_on,
            beginners_corporations_on=beginners_corporations_on,
            game_speed=game_speed,
            game_mode=game_mode,
            players=players_dict
        )
        
        logger.info(f"Successfully parsed table metadata: {len(players_dict)} players, game_mode={game_mode}, map={map_name}")
        return metadata
    
    def convert_assignment_to_game_metadata(self, assignment_data: Dict[str, Any]) -> GameMetadata:
        """Convert GUI assignment data (camelCase) to GameMetadata with EloData objects"""
        logger.info("Converting assignment data to GameMetadata")
        
        players_dict = {}
        for player in assignment_data.get('players', []):
            player_id = str(player.get('playerId', ''))
            if player_id:
                elo_data = EloData(
                    player_name=player.get('playerName'),
                    player_id=player_id,
                    position=player.get('position'),
                    arena_points=player.get('arenaPoints'),
                    arena_points_change=player.get('arenaPointsChange'),
                    game_rank=player.get('elo'),
                    game_rank_change=player.get('eloChange')
                )
                players_dict[player_id] = elo_data
        
        metadata = GameMetadata(
            played_at=assignment_data.get('playedAt'),
            map=assignment_data.get('map'),
            prelude_on=assignment_data.get('preludeOn'),
            colonies_on=assignment_data.get('coloniesOn'),
            corporate_era_on=assignment_data.get('corporateEraOn'),
            draft_on=assignment_data.get('draftOn'),
            beginners_corporations_on=assignment_data.get('beginnersCorporationsOn'),
            game_speed=assignment_data.get('gameSpeed'),
            game_mode=assignment_data.get('gameMode', 'Arena mode'),
            version_id=assignment_data.get('versionId'),
            players=players_dict
        )
        
        logger.info(f"Successfully converted assignment data: {len(players_dict)} players")
        return metadata
    
    def _extract_game_mode_from_table(self, table_html: str) -> str:
        """Extract game mode from table HTML"""
        soup = BeautifulSoup(table_html, 'html.parser')
        span_element = soup.find('span', id='mob_gameoption_201_displayed_value')
        
        if span_element:
            mode = span_element.get_text().strip()
            return mode
        else:
            return "Normal mode"  # Default
    
    def _extract_map_from_table(self, table_html: str) -> Optional[str]:
        """Extract the selected map from table page HTML"""
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            
            # Look for the specific map element
            map_element = soup.find('span', id='gameoption_107_displayed_value')
            
            if map_element:
                map_name = map_element.get_text().strip()
                logger.info(f"Extracted map: {map_name}")
                return map_name
            else:
                logger.debug("Map element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting map from table HTML: {e}")
            return None
    
    def _extract_corporate_era_from_table(self, table_html: str) -> Optional[bool]:
        """Extract the Corporate Era setting from table page HTML"""
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            
            # Look for the specific Corporate Era element
            corporate_era_element = soup.find('span', id='mob_gameoption_101_displayed_value')
            
            if corporate_era_element:
                corporate_era_text = corporate_era_element.get_text().strip()
                corporate_era_on = corporate_era_text.lower() == 'on'
                logger.info(f"Extracted Corporate Era: {corporate_era_text} -> {corporate_era_on}")
                return corporate_era_on
            else:
                logger.debug("Corporate Era element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Corporate Era from table HTML: {e}")
            return None
    
    def _extract_prelude_from_table(self, table_html: str) -> Optional[bool]:
        """Extract the Prelude setting from table page HTML"""
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            
            # Look for the specific Prelude element
            prelude_element = soup.find('span', id='mob_gameoption_104_displayed_value')
            
            if prelude_element:
                prelude_text = prelude_element.get_text().strip()
                prelude_on = prelude_text.lower() == 'on'
                logger.info(f"Extracted Prelude: {prelude_text} -> {prelude_on}")
                return prelude_on
            else:
                logger.debug("Prelude element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Prelude from table HTML: {e}")
            return None
    
    def _extract_draft_from_table(self, table_html: str) -> Optional[bool]:
        """Extract the Draft setting from table page HTML"""
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            
            # Look for the specific Draft element
            draft_element = soup.find('span', id='mob_gameoption_103_displayed_value')
            
            if draft_element:
                draft_text = draft_element.get_text().strip()
                draft_on = draft_text.lower() == 'yes'
                logger.info(f"Extracted Draft: {draft_text} -> {draft_on}")
                return draft_on
            else:
                logger.debug("Draft element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Draft from table HTML: {e}")
            return None
    
    def _extract_colonies_from_table(self, table_html: str) -> Optional[bool]:
        """Extract the Colonies setting from table page HTML"""
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            
            # Look for the specific Colonies element
            colonies_element = soup.find('span', id='mob_gameoption_108_displayed_value')
            
            if colonies_element:
                colonies_text = colonies_element.get_text().strip()
                colonies_on = colonies_text.lower() == 'on'
                logger.info(f"Extracted Colonies: {colonies_text} -> {colonies_on}")
                return colonies_on
            else:
                logger.debug("Colonies element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Colonies from table HTML: {e}")
            return None
    
    def _extract_beginners_corporations_from_table(self, table_html: str) -> Optional[bool]:
        """Extract the Beginners Corporations setting from table page HTML"""
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            
            # Look for the specific Beginners Corporations element
            beginners_corps_element = soup.find('span', id='gameoption_100_displayed_value')
            
            if beginners_corps_element:
                beginners_corps_text = beginners_corps_element.get_text().strip()
                beginners_corps_on = beginners_corps_text.lower() == 'yes'
                logger.info(f"Extracted Beginners Corporations: {beginners_corps_text} -> {beginners_corps_on}")
                return beginners_corps_on
            else:
                logger.debug("Beginners Corporations element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Beginners Corporations from table HTML: {e}")
            return None
    
    def _extract_game_speed_from_table(self, table_html: str) -> Optional[str]:
        """Extract the Game Speed setting from table page HTML"""
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            
            # Look for the specific Game Speed element
            game_speed_element = soup.find('span', id='gameoption_200_displayed_value')
            
            if game_speed_element:
                game_speed_text = game_speed_element.get_text().strip()
                logger.info(f"Extracted Game Speed: {game_speed_text}")
                return game_speed_text
            else:
                logger.debug("Game Speed element not found in table HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Game Speed from table HTML: {e}")
            return None

    def _extract_game_date_from_table(self, table_html: str) -> Optional[Dict]:
        """
        Extract the game creation date from table page HTML
        
        Args:
            table_html: HTML content of the table page
            
        Returns:
            dict: Dictionary with raw_datetime, parsed_datetime, and date_type, or None if not found
        """
        try:
            soup = BeautifulSoup(table_html, 'html.parser')
            
            # Look for the creationtime div
            creationtime_element = soup.find('div', id='creationtime')
            
            if creationtime_element:
                creation_text = creationtime_element.get_text().strip()
                logger.info(f"Found creation time text: {creation_text}")
                
                # Extract the date part after "Created "
                if creation_text.startswith('Created '):
                    date_text = creation_text[8:]  # Remove "Created " prefix
                    
                    # Use the existing _parse_game_datetime method to handle both relative and absolute dates
                    datetime_info = self._parse_game_datetime(date_text)
                    
                    if datetime_info:
                        logger.info(f"Successfully extracted game date from table: {datetime_info['raw_datetime']}")
                        return datetime_info
                    else:
                        logger.warning(f"Could not parse date from: {date_text}")
                else:
                    logger.warning(f"Unexpected creation time format: {creation_text}")
            else:
                logger.debug("Creation time element not found in table HTML")
            
            return None
                
        except Exception as e:
            logger.error(f"Error extracting game date from table HTML: {e}")
            return None

    def _parse_game_datetime(self, text: str) -> Optional[Dict]:
        """
        Parse datetime from text, handling both relative and absolute dates
        
        Args:
            text: Text that may contain datetime information
            
        Returns:
            dict: Dictionary with raw_datetime, parsed_datetime, and date_type, or None if not found
        """
        try:
            # Pattern 1: Relative dates like "yesterday at 00:08"
            relative_pattern = r'(yesterday|today)\s+at\s+(\d{1,2}:\d{2})'
            relative_match = re.search(relative_pattern, text.lower())
            
            if relative_match:
                relative_word = relative_match.group(1)
                time_str = relative_match.group(2)
                
                # Calculate the actual date
                current_date = datetime.now()
                if relative_word == 'yesterday':
                    target_date = current_date - timedelta(days=1)
                else:  # today
                    target_date = current_date
                
                # Parse the time
                time_parts = time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                # Create the full datetime
                parsed_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                return {
                    'raw_datetime': f"{relative_word} at {time_str}",
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date_type': 'relative'
                }
            
            # Pattern 2: Absolute dates like "2025-06-15 at 00:29"
            absolute_pattern = r'(\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2}:\d{2})'
            absolute_match = re.search(absolute_pattern, text)
            
            if absolute_match:
                date_str = absolute_match.group(1)
                time_str = absolute_match.group(2)
                
                # Parse the full datetime
                datetime_str = f"{date_str} {time_str}:00"
                parsed_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                
                return {
                    'raw_datetime': f"{date_str} at {time_str}",
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date_type': 'absolute'
                }
            
            # Pattern 3: Alternative absolute format like "15/06/2025 at 00:29"
            alt_absolute_pattern = r'(\d{1,2}/\d{1,2}/\d{4})\s+at\s+(\d{1,2}:\d{2})'
            alt_absolute_match = re.search(alt_absolute_pattern, text)
            
            if alt_absolute_match:
                date_str = alt_absolute_match.group(1)
                time_str = alt_absolute_match.group(2)
                
                # Parse the date (assuming DD/MM/YYYY format)
                date_parts = date_str.split('/')
                day = int(date_parts[0])
                month = int(date_parts[1])
                year = int(date_parts[2])
                
                # Parse the time
                time_parts = time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                # Create the datetime
                parsed_datetime = datetime(year, month, day, hour, minute, 0)
                
                return {
                    'raw_datetime': f"{date_str} at {time_str}",
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date_type': 'absolute'
                }
            
            # Pattern 4: Just time like "00:08" (assume today)
            time_only_pattern = r'\b(\d{1,2}:\d{2})\b'
            time_only_match = re.search(time_only_pattern, text)
            
            if time_only_match:
                time_str = time_only_match.group(1)
                
                # Parse the time and assume today
                time_parts = time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                current_date = datetime.now()
                parsed_datetime = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                return {
                    'raw_datetime': time_str,
                    'parsed_datetime': parsed_datetime.isoformat(),
                    'date_type': 'time_only'
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing datetime from text '{text}': {e}")
            return None
    
    def parse_complete_game(self, replay_html: str, game_metadata: GameMetadata, table_id: str, player_perspective: str) -> GameData:
        """Unified parsing method that takes GameMetadata instead of separate parameters"""
        logger.info(f"Starting unified parsing for game {table_id}")
        
        soup = BeautifulSoup(replay_html, 'html.parser')
        
        # Extract gamelogs once for memory efficiency
        gamelogs = self._extract_g_gamelogs(replay_html)
        
        # Extract player IDs from GameMetadata
        player_id_map = self._get_player_id_map(game_metadata)
        
        # Extract VP progression throughout the game
        vp_progression = self._extract_vp_progression(replay_html, gamelogs)
        
        # Extract corporations from HTML
        corporations = self._extract_corporations(soup)
        
        # Create simple name_to_id mapping for move processing
        name_to_id = {name: player_id for player_id, name in player_id_map.items()}
        
        # Extract all moves with detailed parsing (using simple name mapping)
        moves = self._extract_all_moves_simple(soup, name_to_id, gamelogs)
        
        # Build game states for each move
        moves_with_states = self._build_game_states_simple(moves, vp_progression, list(player_id_map.keys()), gamelogs)
        
        # Add comprehensive resource/production/tag tracking if gamelogs available
        tracking_progression = []
        if gamelogs and player_id_map:
            logger.info("Adding comprehensive tracking data to game states")
            # Extract tracker dictionary dynamically from HTML
            tracker_dict = self._extract_tracker_dictionary_from_html(replay_html)
            
            # Get player IDs for tracking
            player_ids = list(player_id_map.keys())
            
            # Track resources and production through all moves
            tracking_progression = self._track_resources_and_production(gamelogs, player_ids, tracker_dict)
            
            # Update game states with tracking data
            self._update_game_states_with_tracking(moves_with_states, tracking_progression)

        # Build final player objects from collected data
        players_info = self._build_final_players(player_id_map, corporations, moves_with_states, game_metadata)
        
        # Determine winner from final game state
        winner = self._determine_winner_from_game_states(moves_with_states, players_info)
        
        # Extract game metadata
        metadata = self._extract_metadata(soup, replay_html, moves_with_states)
        
        # Calculate max generation from vp_progression or moves
        max_generation = self._calculate_max_generation(vp_progression, moves_with_states)
        
        # Create game data with game metadata fields
        game_data = GameData(
            replay_id=table_id,
            player_perspective=player_perspective,
            game_date=self._extract_game_date(soup, game_metadata),
            game_duration=self._calculate_game_duration(moves_with_states),
            winner=winner,
            generations=max_generation,
            # Add game metadata fields to top level
            map=game_metadata.map,
            prelude_on=game_metadata.prelude_on,
            colonies_on=game_metadata.colonies_on,
            corporate_era_on=game_metadata.corporate_era_on,
            draft_on=game_metadata.draft_on,
            beginners_corporations_on=game_metadata.beginners_corporations_on,
            game_speed=game_metadata.game_speed,
            players=players_info,
            moves=moves_with_states,
            metadata=metadata
        )
        
        logger.info(f"Unified parsing complete for game {table_id}: {len(moves_with_states)} moves, {len(players_info)} players")
        return game_data
    
    def _get_player_id_map(self, game_metadata: GameMetadata) -> Dict[str, str]:
        """Extract player ID to name mapping from GameMetadata"""
        player_id_map = {}  # player_id -> player_name
        
        if game_metadata and game_metadata.players:
            logger.info("Extracting player IDs from GameMetadata")
            for player_id, elo_data in game_metadata.players.items():
                if elo_data.player_name:
                    player_id_map[player_id] = elo_data.player_name
                    logger.debug(f"GameMetadata: {player_id} -> {elo_data.player_name}")
            
            if player_id_map:
                logger.info(f"Successfully extracted {len(player_id_map)} players from GameMetadata")
                return player_id_map
        
        # If no player data available, raise an error
        logger.error("No player data available in GameMetadata")
        raise ValueError("Parser requires GameMetadata with player information")
    
    def _build_final_players(self, player_id_map: Dict[str, str], corporations: Dict[str, str], 
                                               moves_with_states: List[Move], game_metadata: GameMetadata) -> Dict[str, Player]:
        """Build final player objects from collected data using GameMetadata"""
        players = {}
        
        # Get final VP data from the last move with game state
        final_vp_data = {}
        if moves_with_states:
            for move in reversed(moves_with_states):
                if move.game_state and move.game_state.player_vp:
                    final_vp_data = move.game_state.player_vp
                    break
        
        # Build player objects
        for player_id, player_name in player_id_map.items():
            # Get final VP and breakdown
            final_vp = 0
            vp_breakdown = {}
            if player_id in final_vp_data:
                final_vp = final_vp_data[player_id].get('total', 0)
                vp_breakdown = final_vp_data[player_id].get('total_details', {})
            
            # Collect cards played, milestones, awards from moves
            cards_played = []
            milestones_claimed = []
            awards_funded = []
            
            for move in moves_with_states:
                if move.player_id == player_id:
                    if move.card_played:
                        cards_played.append(move.card_played)
                    if move.action_type == 'claim_milestone':
                        milestone_match = re.search(r'claims milestone (\w+)', move.description)
                        if milestone_match:
                            milestones_claimed.append(milestone_match.group(1))
                    if move.action_type == 'fund_award':
                        award_match = re.search(r'funds (\w+) award', move.description)
                        if award_match:
                            awards_funded.append(award_match.group(1))
            
            # Get ELO data from GameMetadata
            elo_data = None
            if game_metadata and game_metadata.players and player_id in game_metadata.players:
                elo_data = game_metadata.players[player_id]
            
            players[player_id] = Player(
                player_id=player_id,
                player_name=player_name,
                corporation=corporations.get(player_name, 'Unknown'),
                final_vp=final_vp,
                final_tr=vp_breakdown.get('tr', 20),
                vp_breakdown=vp_breakdown,
                cards_played=cards_played,
                milestones_claimed=milestones_claimed,
                awards_funded=awards_funded,
                elo_data=elo_data
            )
        
        logger.info(f"Built {len(players)} final player objects from GameMetadata")
        return players
    
    def _extract_game_date(self, soup: BeautifulSoup, game_metadata: GameMetadata) -> str:
        """Extract game date from GameMetadata or HTML"""
        # If GameMetadata has played_at timestamp, use it
        if game_metadata and game_metadata.played_at:
            try:
                # Parse the ISO timestamp and convert to date
                played_at_dt = datetime.fromisoformat(game_metadata.played_at.replace('Z', '+00:00'))
                return played_at_dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse played_at timestamp '{game_metadata.played_at}': {e}")
        
        # Fallback: Look for date information in the HTML
        # This would need to be customized based on BGA's HTML structure
        return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_all_moves(self, soup: BeautifulSoup, players_info: Dict[str, Player], gamelogs: Dict[str, Any] = None) -> List[Move]:
        """Extract all moves with detailed information"""
        moves = []
        move_divs = soup.find_all('div', class_='replaylogs_move')
        
        # Create reverse lookup for player names to IDs
        name_to_id = {player.player_name: player_id for player_id, player in players_info.items()}
        
        for move_div in move_divs:
            move = self._parse_single_move_detailed(move_div, name_to_id, gamelogs)
            if move:
                moves.append(move)
                
                # Update player data based on move
                self._update_player_data_from_move(move, players_info)
        
        return moves
    
    def _parse_single_move_detailed(self, move_div: Tag, name_to_id: Dict[str, str], gamelogs: Dict[str, Any] = None) -> Optional[Move]:
        """Parse a single move with comprehensive detail extraction"""
        try:
            # Extract move number and timestamp
            move_info = move_div.find('div', class_='smalltext')
            if not move_info:
                return None
            
            move_text = move_info.get_text()
            move_match = re.search(r'Move (\d+)', move_text)
            if not move_match:
                return None
            
            move_number = int(move_match.group(1))
            
            # Extract timestamp
            timestamp_match = re.search(r'(\d{1,2}:\d{2}:\d{2})', move_text)
            timestamp = timestamp_match.group(1) if timestamp_match else ""
            
            # Extract all log entries
            log_entries = move_div.find_all('div', class_='gamelogreview')
            if not log_entries:
                return None
            
            # Combine descriptions
            descriptions = [entry.get_text().strip() for entry in log_entries]
            full_description = ' | '.join(descriptions)
            
            # Determine player - use gamelogs first, then fallback to HTML parsing
            player_name, player_id = self._determine_player_from_gamelogs(move_number, gamelogs, name_to_id)
            if player_id == "unknown":
                # Fallback to HTML-based player determination
                player_name, player_id = self._determine_move_player(log_entries, full_description, name_to_id)
            
            # Extract action details
            action_type = self._classify_action_type(log_entries, full_description)
            card_played = self._extract_card_played(log_entries)
            tile_placed, tile_location = self._extract_tile_placement(log_entries)
            
            move = Move(
                move_number=move_number,
                timestamp=timestamp,
                player_id=player_id,
                player_name=player_name,
                action_type=action_type,
                description=full_description,
                card_played=card_played,
                tile_placed=tile_placed,
                tile_location=tile_location
            )
            
            return move
            
        except Exception as e:
            logger.error(f"Error parsing move: {e}")
            return None
    
    def _determine_player_from_gamelogs(self, move_number: int, gamelogs: Dict[str, Any], name_to_id: Dict[str, str]) -> Tuple[str, str]:
        """Determine which player made this move using gamelogs data (preferred method)"""
        if not gamelogs:
            return "Unknown", "unknown"
        
        try:
            # Find the move entry in gamelogs
            data_entries = gamelogs.get('data', {}).get('data', [])
            move_entry = None
            
            for entry in data_entries:
                if entry.get('move_id') == str(move_number):
                    move_entry = entry
                    break
            
            if not move_entry:
                logger.debug(f"No gamelogs entry found for move {move_number}")
                return "Unknown", "unknown"
            
            # Check the first data item in the move for player information
            move_data = move_entry.get('data', [])
            if not move_data:
                logger.debug(f"No data found in gamelogs for move {move_number}")
                return "Unknown", "unknown"
            
            # Get the first data item (usually contains the main action)
            first_data_item = move_data[0]
            args = first_data_item.get('args', {})
            
            # Check for active_player first (preferred)
            if 'active_player' in args:
                player_id = str(args['active_player'])
                logger.debug(f"Move {move_number}: Found active_player = {player_id}")
            elif 'player_id' in args:
                player_id = str(args['player_id'])
                logger.debug(f"Move {move_number}: Found player_id = {player_id}")
            else:
                logger.debug(f"Move {move_number}: No player ID found in gamelogs args")
                return None, None
            
            # Try to find the player name from the name_to_id mapping
            for player_name, mapped_id in name_to_id.items():
                if mapped_id == player_id:
                    logger.debug(f"Move {move_number}: Mapped player_id {player_id} to {player_name}")
                    return player_name, player_id
            
            # If no mapping found, return the player_id as both name and id
            logger.debug(f"Move {move_number}: No name mapping found for player_id {player_id}, using ID as name")
            return f"Player_{player_id}", player_id
            
        except Exception as e:
            logger.error(f"Error determining player from gamelogs for move {move_number}: {e}")
            return "Unknown", "unknown"
    
    def _determine_move_player(self, log_entries: List[Tag], description: str, name_to_id: Dict[str, str]) -> Tuple[str, str]:
        """Determine which player made this move (fallback method using HTML parsing)"""
        # Look for explicit player mentions
        for entry in log_entries:
            text = entry.get_text()
            
            # Check for player names in the text
            for player_name in name_to_id.keys():
                if player_name in text and any(verb in text for verb in ['plays', 'pays', 'gains', 'increases', 'reduces', 'places', 'chooses']):
                    return player_name, name_to_id[player_name]
            
            # Handle "You" references - would need context to resolve properly
            if text.startswith('You '):
                # For now, return as "You" - could be improved with more context
                return "You", "you"
        
        return "Unknown", "unknown"
    
    def _classify_action_type(self, log_entries: List[Tag], description: str) -> str:
        """Classify the type of action"""
        if 'plays card' in description:
            return 'play_card'
        elif any(phrase in description for phrase in ['places City', 'places Forest', 'places Ocean']):
            return 'place_tile'
        elif 'standard project' in description:
            return 'standard_project'
        elif 'passes' in description:
            return 'pass'
        elif 'Convert heat into temperature' in description:
            return 'convert_heat'
        elif 'claims milestone' in description:
            return 'claim_milestone'
        elif 'funds' in description and 'award' in description:
            return 'fund_award'
        elif 'activates' in description:
            return 'activate_card'
        elif 'New generation' in description:
            return 'new_generation'
        elif 'draft' in description:
            return 'draft_card'
        elif 'Buy Card' in description:
            return 'buy_card'
        else:
            return 'other'
    
    def _extract_card_played(self, log_entries: List[Tag]) -> Optional[str]:
        """Extract the name of the card played"""
        for entry in log_entries:
            text = entry.get_text()
            if 'plays card' in text:
                card_link = entry.find('div', class_='card_hl_tt')
                if card_link:
                    return card_link.get_text().strip()
                else:
                    # Fallback: extract from text
                    match = re.search(r'plays card (.+)', text)
                    if match:
                        return match.group(1).strip()
        return None
    
    def _extract_tile_placement(self, log_entries: List[Tag]) -> Tuple[Optional[str], Optional[str]]:
        """Extract tile placement information"""
        for entry in log_entries:
            text = entry.get_text()
            if 'places' in text:
                if 'places City on' in text:
                    tile_type = "City"
                    location_match = re.search(r'places City on (.+)', text)
                elif 'places Forest on' in text:
                    tile_type = "Forest"
                    location_match = re.search(r'places Forest on (.+)', text)
                elif 'places Ocean on' in text:
                    tile_type = "Ocean"
                    location_match = re.search(r'places Ocean on (.+)', text)
                else:
                    continue
                
                location = location_match.group(1).strip() if location_match else "Unknown"
                return tile_type, location
        
        return None, None
    
    def _extract_parameter_changes_from_gamelogs(self, gamelogs: Dict[str, Any]) -> Dict[int, Dict[str, int]]:
        """Extract terraforming parameter changes from gamelogs JSON data"""
        parameter_changes_by_move = {}
        
        try:
            data_entries = gamelogs.get('data', {}).get('data', [])
            
            for entry in data_entries:
                if not isinstance(entry, dict):
                    continue
                
                move_id = entry.get('move_id')
                if not move_id:
                    continue
                
                try:
                    move_number = int(move_id)
                except (ValueError, TypeError):
                    continue
                
                # Process all data items in this move
                entry_data = entry.get('data', [])
                if not isinstance(entry_data, list):
                    continue
                
                move_changes = {}
                
                for data_item in entry_data:
                    if not isinstance(data_item, dict):
                        continue
                    
                    # Look for counter updates with global parameter trackers
                    if data_item.get('type') == 'counter':
                        args = data_item.get('args', {})
                        token_name = args.get('token_name', '')
                        counter_value = args.get('counter_value')
                        
                        if counter_value is not None:
                            try:
                                value = int(counter_value)
                                
                                # Map tracker names to parameters
                                if token_name == 'tracker_t':  # Temperature
                                    move_changes['temperature'] = value
                                    logger.debug(f"Move {move_number}: Found temperature = {value}")
                                elif token_name == 'tracker_o':  # Oxygen
                                    move_changes['oxygen'] = value
                                    logger.debug(f"Move {move_number}: Found oxygen = {value}")
                                elif token_name == 'tracker_w':  # Oceans
                                    move_changes['oceans'] = value
                                    logger.debug(f"Move {move_number}: Found oceans = {value}")
                                    
                            except (ValueError, TypeError):
                                continue
                
                # Store changes for this move if any were found
                if move_changes:
                    parameter_changes_by_move[move_number] = move_changes
                    logger.debug(f"Move {move_number}: Parameter changes = {move_changes}")
            
            logger.info(f"Extracted parameter changes for {len(parameter_changes_by_move)} moves from gamelogs")
            return parameter_changes_by_move
            
        except Exception as e:
            logger.error(f"Error extracting parameter changes from gamelogs: {e}")
            return {}
    
    def _update_player_data_from_move(self, move: Move, players_info: Dict[str, Player]):
        """Update player data based on move information"""
        if move.player_id not in players_info:
            return
        
        player = players_info[move.player_id]
        
        # Track cards played
        if move.card_played:
            player.cards_played.append(move.card_played)
        
        # Track milestones claimed
        if move.action_type == 'claim_milestone':
            milestone_match = re.search(r'claims milestone (\w+)', move.description)
            if milestone_match:
                player.milestones_claimed.append(milestone_match.group(1))
        
        # Track awards funded
        if move.action_type == 'fund_award':
            award_match = re.search(r'funds (\w+) award', move.description)
            if award_match:
                player.awards_funded.append(award_match.group(1))
    
    def _build_game_states(self, moves: List[Move], vp_progression: List[Dict[str, Any]], players_info: Dict[str, Player], gamelogs: Dict[str, Any] = None) -> List[Move]:
        """Build game states for each move with VP, milestone, and award tracking"""
        # Initialize tracking variables
        current_temp = -30
        current_oxygen = 0
        current_oceans = 0
        current_generation = 1
        
        # Track milestones and awards state throughout the game
        current_milestones = {}
        current_awards = {}
        
        # Initialize default VP data for all players
        default_vp_data = {}
        for player_id in players_info.keys():
            default_vp_data[player_id] = {
                "total": 20,
                "total_details": {
                    "tr": 20,
                    "awards": 0,
                    "milestones": 0,
                    "cities": 0,
                    "greeneries": 0,
                    "cards": 0
                }
            }
        
        # Track the last known VP data to carry forward when no new data is available
        last_vp_data = dict(default_vp_data)
        
        # Create a mapping from move_number to VP data for proper correlation
        vp_by_move_number = {}
        for vp_entry in vp_progression:
            move_number = vp_entry.get('move_number')
            if move_number:
                # Convert move_number to string for consistent matching
                vp_by_move_number[str(move_number)] = vp_entry.get('vp_data', {})
        
        logger.info(f"Built VP mapping for {len(vp_by_move_number)} moves")
        
        # Extract parameter changes from gamelogs if available
        parameter_changes_by_move = {}
        if gamelogs:
            parameter_changes_by_move = self._extract_parameter_changes_from_gamelogs(gamelogs)
            logger.info(f"Extracted parameter changes for {len(parameter_changes_by_move)} moves from gamelogs")
        
        # Process each move and build game state
        for i, move in enumerate(moves):
            # Update generation
            if 'New generation' in move.description:
                gen_match = re.search(r'New generation (\d+)', move.description)
                if gen_match:
                    current_generation = int(gen_match.group(1))
            
            # Update parameters from gamelogs data
            move_parameter_changes = parameter_changes_by_move.get(move.move_number, {})
            if move_parameter_changes:
                if 'temperature' in move_parameter_changes:
                    current_temp = move_parameter_changes['temperature']
                    logger.debug(f"Move {move.move_number}: Temperature updated to {current_temp}")
                if 'oxygen' in move_parameter_changes:
                    current_oxygen = move_parameter_changes['oxygen']
                    logger.debug(f"Move {move.move_number}: Oxygen updated to {current_oxygen}")
                if 'oceans' in move_parameter_changes:
                    current_oceans = move_parameter_changes['oceans']
                    logger.debug(f"Move {move.move_number}: Oceans updated to {current_oceans}")
            
            # Update milestone and award tracking
            if move.action_type == 'claim_milestone':
                milestone_match = re.search(r'claims milestone (\w+)', move.description)
                if milestone_match:
                    milestone_name = milestone_match.group(1)
                    current_milestones[milestone_name] = {
                        'claimed_by': move.player_name,
                        'player_id': move.player_id,
                        'move_number': move.move_number,
                        'timestamp': move.timestamp
                    }
            
            if move.action_type == 'fund_award':
                award_match = re.search(r'funds (\w+) award', move.description)
                if award_match:
                    award_name = award_match.group(1)
                    current_awards[award_name] = {
                        'funded_by': move.player_name,
                        'player_id': move.player_id,
                        'move_number': move.move_number,
                        'timestamp': move.timestamp
                    }
            
            # Get VP data for this move by matching move_number
            move_vp_data = vp_by_move_number.get(str(move.move_number), {})
            
            # Ensure VP data is always present
            if move_vp_data:
                # Update last known VP data with new data
                last_vp_data = dict(move_vp_data)
                logger.debug(f"Updated VP data for move {move.move_number}")
            else:
                # Use last known VP data if no new data available
                move_vp_data = dict(last_vp_data)
                logger.debug(f"Using carried-forward VP data for move {move.move_number}")
            
            # Ensure all players have VP data (fill in missing players with defaults)
            for player_id in players_info.keys():
                if player_id not in move_vp_data:
                    move_vp_data[player_id] = dict(default_vp_data[player_id])
                    logger.debug(f"Added default VP data for missing player {player_id} in move {move.move_number}")
            
            # Create game state (without resource/production tracking)
            game_state = GameState(
                move_number=move.move_number,
                generation=current_generation,
                temperature=current_temp,
                oxygen=current_oxygen,
                oceans=current_oceans,
                player_vp=move_vp_data,
                milestones=dict(current_milestones),
                awards=dict(current_awards)
            )
            
            move.game_state = game_state
        
        return moves
    
    def _extract_card_names(self, html_content: str) -> Dict[str, str]:
        """Extract card ID to name mappings from HTML"""
        card_names = {}
        
        try:
            # Pattern to match card elements with data-name attributes
            pattern = r'<div[^>]+id="(card_[^"]+)"[^>]+data-name="([^"]+)"'
            matches = re.findall(pattern, html_content)
            
            for card_id, card_name in matches:
                # Clean up the card ID (remove _help suffix if present)
                clean_id = card_id.replace('_help', '')
                card_names[clean_id] = card_name
            
            logger.info(f"Extracted {len(card_names)} card name mappings")
            return card_names
            
        except Exception as e:
            logger.error(f"Error extracting card names: {e}")
            return {}
    
    def _extract_milestone_names(self, html_content: str) -> Dict[str, str]:
        """Extract milestone ID to name mappings from HTML"""
        milestone_names = {}
        
        try:
            # Pattern to match milestone elements with data-name attributes
            pattern = r'<div[^>]+id="(milestone_\d+)"[^>]+data-name="([^"]+)"'
            matches = re.findall(pattern, html_content)
            
            for milestone_id, milestone_name in matches:
                milestone_names[milestone_id] = milestone_name
            
            logger.info(f"Extracted {len(milestone_names)} milestone name mappings")
            return milestone_names
            
        except Exception as e:
            logger.error(f"Error extracting milestone names: {e}")
            return {}
    
    def _extract_award_names(self, html_content: str) -> Dict[str, str]:
        """Extract award ID to name mappings from HTML"""
        award_names = {}
        
        try:
            # Pattern to match award elements with data-name attributes
            pattern = r'<div[^>]+id="(award_\d+)"[^>]+data-name="([^"]+)"'
            matches = re.findall(pattern, html_content)
            
            for award_id, award_name in matches:
                award_names[award_id] = award_name
            
            logger.info(f"Extracted {len(award_names)} award name mappings")
            return award_names
            
        except Exception as e:
            logger.error(f"Error extracting award names: {e}")
            return {}

    def _extract_hex_names(self, html_content: str) -> Dict[str, str]:
        """Extract hex ID to name mappings from HTML hex map"""
        hex_names = {}
        
        try:
            # Pattern to match hex elements with data-name attributes
            pattern = r'<div[^>]+id="(hex_\d+_\d+)"[^>]+data-name="([^"]+)"'
            matches = re.findall(pattern, html_content)
            
            for hex_id, hex_name in matches:
                hex_names[hex_id] = hex_name
            
            logger.info(f"Extracted {len(hex_names)} hex name mappings")
            return hex_names
            
        except Exception as e:
            logger.error(f"Error extracting hex names: {e}")
            return {}

    def _extract_tile_to_hex_mapping(self, gamelogs: Dict[str, Any]) -> Dict[str, str]:
        """Extract tile ID to hex ID mappings from gamelogs"""
        tile_to_hex = {}
        
        try:
            data_entries = gamelogs.get('data', {}).get('data', [])
            
            for entry in data_entries:
                if not isinstance(entry, dict):
                    continue
                
                entry_data = entry.get('data', [])
                if not isinstance(entry_data, list):
                    continue
                
                for data_item in entry_data:
                    if not isinstance(data_item, dict):
                        continue
                    
                    # Look for tile placement events
                    args = data_item.get('args', {})
                    if 'token_id' in args and 'place_id' in args:
                        token_id = args['token_id']
                        place_id = args['place_id']
                        
                        # Only map tile tokens to hex places
                        if token_id.startswith('tile_') and place_id.startswith('hex_'):
                            tile_to_hex[token_id] = place_id
                            logger.debug(f"Mapped tile {token_id} to hex {place_id}")
            
            logger.info(f"Extracted {len(tile_to_hex)} tile-to-hex mappings")
            return tile_to_hex
            
        except Exception as e:
            logger.error(f"Error extracting tile-to-hex mapping: {e}")
            return {}

    def _extract_g_gamelogs(self, html_content: str) -> Dict[str, Any]:
        """Extract g_gamelogs JSON with proper brace balancing"""
        try:
            # Find the start of g_gamelogs
            pattern = r'g_gamelogs\s*=\s*'
            match = re.search(pattern, html_content)
            
            if not match:
                logger.warning("g_gamelogs not found in HTML")
                return {}
            
            start_pos = match.end()
            
            # Find the complete JSON object by counting braces
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(html_content[start_pos:], start_pos):
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # Found the end of the JSON object
                            json_str = html_content[start_pos:i+1]
                            return json.loads(json_str)
                    elif char == ';' and brace_count == 0:
                        # Hit semicolon before closing brace - malformed
                        break
            
            logger.error("Could not find complete g_gamelogs JSON")
            return {}
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Error extracting g_gamelogs: {e}")
            return {}
    
    def _replace_ids_with_names(self, vp_data: Dict[str, Any], card_names: Dict[str, str], 
                               milestone_names: Dict[str, str], award_names: Dict[str, str],
                               tile_to_hex: Dict[str, str] = None, hex_names: Dict[str, str] = None) -> Dict[str, Any]:
        """Replace ID references with actual names in VP data, including hex information for tiles"""
        if not isinstance(vp_data, dict):
            return vp_data
        
        # Default to empty dicts if not provided
        if tile_to_hex is None:
            tile_to_hex = {}
        if hex_names is None:
            hex_names = {}
        
        updated_data = {}
        
        for player_id, player_vp in vp_data.items():
            if not isinstance(player_vp, dict):
                updated_data[player_id] = player_vp
                continue
            
            updated_player_vp = dict(player_vp)
            
            # Process the details section
            if 'details' in updated_player_vp and isinstance(updated_player_vp['details'], dict):
                details = updated_player_vp['details']
                updated_details = {}
                
                for category, items in details.items():
                    # Skip TR category since it's already in total_details
                    if category == 'tr':
                        continue
                        
                    if not isinstance(items, dict):
                        updated_details[category] = items
                        continue
                    
                    updated_items = {}
                    
                    for item_id, item_data in items.items():
                        # Determine the actual name based on category and ID
                        actual_name = item_id  # Default to original ID
                        
                        if category == 'cards' and item_id in card_names:
                            actual_name = card_names[item_id]
                        elif category == 'milestones' and item_id in milestone_names:
                            actual_name = milestone_names[item_id]
                        elif category == 'awards' and item_id in award_names:
                            actual_name = award_names[item_id]
                        
                        # Handle tile placement data (cities, greeneries, etc.)
                        updated_item_data = dict(item_data) if isinstance(item_data, dict) else item_data
                        
                        if category in ['cities', 'greeneries'] and item_id.startswith('tile_'):
                            # Use hex name as the key instead of tile ID
                            hex_id = tile_to_hex.get(item_id)
                            if hex_id:
                                hex_name = hex_names.get(hex_id)
                                if hex_name:
                                    # Use hex name as the actual name instead of tile ID
                                    actual_name = hex_name
                                    logger.debug(f"Mapped tile {item_id} to hex name: {hex_name}")
                        
                        updated_items[actual_name] = updated_item_data
                    
                    updated_details[category] = updated_items
                
                updated_player_vp['details'] = updated_details
            
            updated_data[player_id] = updated_player_vp
        
        return updated_data

    def _parse_scoring_data_from_gamelogs(self, gamelogs: Dict[str, Any], card_names: Dict[str, str], 
                                        milestone_names: Dict[str, str], award_names: Dict[str, str]) -> List[Dict[str, Any]]:
        """Parse scoring data from g_gamelogs entries and replace IDs with names"""
        scoring_entries = []
        
        try:
            # Extract hex mappings for tile placement data
            hex_names = self._extract_hex_names_from_gamelogs_context(gamelogs)
            tile_to_hex = self._extract_tile_to_hex_mapping(gamelogs)
            
            data_entries = gamelogs.get('data', {}).get('data', [])
            
            for entry in data_entries:
                if not isinstance(entry, dict):
                    continue
                
                # Look for data array within each entry
                entry_data = entry.get('data', [])
                if not isinstance(entry_data, list):
                    continue
                
                for data_item in entry_data:
                    if not isinstance(data_item, dict):
                        continue
                    
                    # Look for scoringTable type entries
                    if data_item.get('type') == 'scoringTable':
                        scoring_data = data_item.get('args', {}).get('data', {})

                        if not scoring_data:
                            scoring_data = data_item.get('args', {}) # Older format

                        if scoring_data:
                            # Replace IDs with names in the scoring data, including hex information
                            scoring_data_with_names = self._replace_ids_with_names(
                                scoring_data, card_names, milestone_names, award_names,
                                tile_to_hex, hex_names
                            )
                            
                            scoring_entry = {
                                'move_id': entry.get('move_id'),
                                'time': entry.get('time'),
                                'uid': data_item.get('uid'),
                                'scoring_data': scoring_data_with_names
                            }
                            scoring_entries.append(scoring_entry)
            
            logger.info(f"Extracted {len(scoring_entries)} scoring entries from g_gamelogs")
            return scoring_entries
            
        except Exception as e:
            logger.error(f"Error parsing scoring data from g_gamelogs: {e}")
            return []

    def _extract_hex_names_from_gamelogs_context(self, gamelogs: Dict[str, Any]) -> Dict[str, str]:
        """Extract hex names from the context where gamelogs are used (fallback method)"""
        # This is a placeholder method - in practice, hex names should be extracted from HTML
        # This method exists to maintain consistency when gamelogs are processed separately
        return {}

    def _extract_vp_progression(self, html_content: str, gamelogs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract VP progression throughout the game using g_gamelogs data"""

        # Extract name mappings from HTML
        card_names = self._extract_card_names(html_content)
        milestone_names = self._extract_milestone_names(html_content)
        award_names = self._extract_award_names(html_content)
        hex_names = self._extract_hex_names(html_content)
        
        # Extract tile-to-hex mapping from gamelogs
        tile_to_hex = self._extract_tile_to_hex_mapping(gamelogs)
        
        # Parse scoring data from g_gamelogs with name replacement including hex information
        scoring_entries = self._parse_scoring_data_from_gamelogs_with_hex(
            gamelogs, card_names, milestone_names, award_names, tile_to_hex, hex_names
        )
        
        vp_progression = []
        for i, entry in enumerate(scoring_entries):
            scoring_data = entry['scoring_data']
            
            # Calculate combined total
            combined_total = sum(data.get('total', 0) for data in scoring_data.values())
            
            vp_entry = {
                'move_number': entry.get('move_id'),
                'time': entry.get('time'),
                'combined_total': combined_total,
                'vp_data': scoring_data
            }
            
            vp_progression.append(vp_entry)
        
        logger.info(f"Extracted VP progression with {len(vp_progression)} entries")
        return vp_progression

    def _parse_scoring_data_from_gamelogs_with_hex(self, gamelogs: Dict[str, Any], card_names: Dict[str, str], 
                                                  milestone_names: Dict[str, str], award_names: Dict[str, str],
                                                  tile_to_hex: Dict[str, str], hex_names: Dict[str, str]) -> List[Dict[str, Any]]:
        """Parse scoring data from g_gamelogs entries with hex information included"""
        scoring_entries = []
        
        try:
            data_entries = gamelogs.get('data', {}).get('data', [])
            
            for entry in data_entries:
                if not isinstance(entry, dict):
                    continue
                
                # Look for data array within each entry
                entry_data = entry.get('data', [])
                if not isinstance(entry_data, list):
                    continue
                
                for data_item in entry_data:
                    if not isinstance(data_item, dict):
                        continue
                    
                    # Look for scoringTable type entries
                    if data_item.get('type') == 'scoringTable':

                        scoring_data = data_item.get('args', {}).get('data', {})

                        if not scoring_data:
                            scoring_data = data_item.get('args', {})

                        if scoring_data:
                            # Replace IDs with names in the scoring data, including hex information
                            scoring_data_with_names = self._replace_ids_with_names(
                                scoring_data, card_names, milestone_names, award_names,
                                tile_to_hex, hex_names
                            )
                            
                            scoring_entry = {
                                'move_id': entry.get('move_id'),
                                'time': entry.get('time'),
                                'uid': data_item.get('uid'),
                                'scoring_data': scoring_data_with_names
                            }
                            scoring_entries.append(scoring_entry)
            
            logger.info(f"Extracted {len(scoring_entries)} scoring entries with hex information from g_gamelogs")
            return scoring_entries
            
        except Exception as e:
            logger.error(f"Error parsing scoring data with hex information from g_gamelogs: {e}")
            return []
    
    def _extract_vp_progression_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """Fallback VP progression extraction using the old regex method"""
        pattern = r'"data":\{((?:"(\d+)":\{[^}]*"total":(\d+)[^}]*\}[,\s]*)+)\}'
        
        matches = re.findall(pattern, html_content, re.DOTALL)
        vp_progression = []
        
        for i, match_data in enumerate(matches):
            try:
                json_str = "{" + match_data[0] + "}"
                
                # Fix JSON structure if needed
                brace_count = match_data[0].count('{') - match_data[0].count('}')
                if brace_count > 0:
                    json_str = "{" + match_data[0] + '}' * brace_count + "}"
                
                vp_data = json.loads(json_str)
                
                # Calculate combined total
                combined_total = sum(data.get('total', 0) for data in vp_data.values())
                
                vp_entry = {
                    'move_number': i + 1,  # Convert 0-based index to 1-based move number
                    'combined_total': combined_total,
                    'vp_data': vp_data
                }
                
                vp_progression.append(vp_entry)
                
            except json.JSONDecodeError:
                continue
        
        return vp_progression
    
    def _extract_vp_data_from_html(self, html_content: str) -> Dict[str, Any]:
        """Extract VP data from HTML - handles both newer and older formats with variable player counts"""
        logger.debug("Extracting VP data from HTML")
        
        # Try newer format first (with "data" wrapper in scoringTable)
        newer_pattern = r'"type":"scoringTable"[^}]*?"args":\s*\{\s*"data":\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
        matches = re.findall(newer_pattern, html_content, re.DOTALL)
        
        if matches:
            logger.debug(f"Found {len(matches)} matches with newer format")
            # Try to parse each match and find the one with highest total VP
            best_vp_data = None
            best_total = 0
            
            for match in matches:
                try:
                    vp_data = json.loads(match)
                    # Calculate total VP across all players
                    total_vp = sum(player_data.get('total', 0) for player_data in vp_data.values() if isinstance(player_data, dict))
                    
                    if total_vp > best_total:
                        best_total = total_vp
                        best_vp_data = vp_data
                        logger.debug(f"Found better VP data with total {total_vp}")
                        
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse newer format match: {e}")
                    continue
            
            if best_vp_data:
                logger.info(f"Successfully extracted VP data (newer format) for {len(best_vp_data)} players, total VP: {best_total}")
                return best_vp_data
        
        # Try older format (direct player data in scoringTable args)
        older_pattern = r'"type":"scoringTable"[^}]*?"args":\s*(\{"[0-9]+":.*?\})'
        matches = re.findall(older_pattern, html_content, re.DOTALL)
        
        if matches:
            logger.debug(f"Found {len(matches)} matches with older format")
            # Try to parse each match and find the one with highest total VP
            best_vp_data = None
            best_total = 0
            
            for match in matches:
                try:
                    # Need to properly close the JSON - find the end of the player data
                    # Look for the complete args object
                    args_start = html_content.find(match)
                    if args_start == -1:
                        continue
                    
                    # Find the closing brace for the args object
                    brace_count = 0
                    end_pos = args_start
                    in_string = False
                    escape_next = False
                    
                    for i, char in enumerate(html_content[args_start:], args_start):
                        if escape_next:
                            escape_next = False
                            continue
                            
                        if char == '\\':
                            escape_next = True
                            continue
                            
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                            
                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_pos = i + 1
                                    break
                    
                    # Extract the complete JSON
                    complete_json = html_content[args_start:end_pos]
                    vp_data = json.loads(complete_json)
                    
                    # Calculate total VP across all players
                    total_vp = sum(player_data.get('total', 0) for player_data in vp_data.values() if isinstance(player_data, dict))
                    
                    if total_vp > best_total:
                        best_total = total_vp
                        best_vp_data = vp_data
                        logger.debug(f"Found better VP data with total {total_vp}")
                        
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse older format match: {e}")
                    continue
            
            if best_vp_data:
                logger.info(f"Successfully extracted VP data (older format) for {len(best_vp_data)} players, total VP: {best_total}")
                return best_vp_data
        
        # Final fallback - try the original regex approach for backwards compatibility
        logger.debug("Trying original regex fallback")
        original_pattern = r'"data":\{("(\d+)":\{.*?"total":(\d+).*?\}.*?"(\d+)":\{.*?"total":(\d+).*?\})\}'
        matches = re.findall(original_pattern, html_content, re.DOTALL)
        
        if matches:
            best_match = None
            best_total = 0
            
            for match_data, player1_id, total1, player2_id, total2 in matches:
                combined_total = int(total1) + int(total2)
                if combined_total > best_total:
                    best_total = combined_total
                    best_match = match_data
            
            if best_match:
                try:
                    json_str = "{" + best_match + "}"
                    brace_count = best_match.count('{') - best_match.count('}')
                    if brace_count > 0:
                        json_str = "{" + best_match + '}' * brace_count + "}"
                    
                    result = json.loads(json_str)
                    logger.info(f"Successfully extracted VP data (fallback) for {len(result)} players")
                    return result
                except json.JSONDecodeError:
                    pass
        
        logger.warning("Failed to extract VP data from HTML using all methods")
        return {}
    
    def _extract_corporations(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract corporation assignments"""
        corporations = {}
        
        # Look for corporation mentions in the log
        log_entries = soup.find_all('div', class_='gamelogreview')
        for entry in log_entries:
            text = entry.get_text()
            if 'chooses corporation' in text:
                # Pattern: "PlayerName chooses corporation CorporationName"
                # Updated to handle multi-word player names and corporation names
                # Use greedy matching for corporation name to capture full names like "Cheung Shing Mars"
                match = re.search(r'([A-Za-z][A-Za-z0-9\s_]+?) chooses corporation ([A-Za-z][A-Za-z0-9\s]+)(?:\s*\||$)', text)
                if match:
                    player_name = match.group(1).strip()
                    corp_name = match.group(2).strip()
                    corporations[player_name] = corp_name
                    logger.info(f"Extracted corporation: {player_name} -> {corp_name}")
                else:
                    # Fallback pattern for simpler cases - also use greedy matching
                    fallback_match = re.search(r'(\w+(?:\s+\w+)*) chooses corporation ([A-Za-z][A-Za-z0-9\s]+)', text)
                    if fallback_match:
                        player_name = fallback_match.group(1).strip()
                        corp_name = fallback_match.group(2).strip()
                        corporations[player_name] = corp_name
                        logger.info(f"Extracted corporation (fallback): {player_name} -> {corp_name}")
        
        logger.info(f"Total corporations extracted: {corporations}")
        return corporations
    
    def _calculate_game_duration(self, moves: List[Move]) -> str:
        """Calculate game duration from moves"""
        if not moves or len(moves) < 2:
            return "Unknown"
        
        try:
            start_time = moves[0].timestamp
            end_time = moves[-1].timestamp
            
            # Parse timestamps (assuming HH:MM:SS format)
            start_parts = start_time.split(':')
            end_parts = end_time.split(':')
            
            start_seconds = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + int(start_parts[2])
            end_seconds = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + int(end_parts[2])
            
            duration_seconds = end_seconds - start_seconds
            if duration_seconds < 0:  # Handle day rollover
                duration_seconds += 24 * 3600
            
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            
            return f"{hours:02d}:{minutes:02d}"
            
        except (ValueError, IndexError):
            return "Unknown"
    
    def _calculate_max_generation(self, vp_progression: List[Dict[str, Any]], moves: List[Move]) -> int:
        """Calculate the maximum generation from vp_progression or moves data"""
        max_generation = 1  # Default to generation 1
        
        try:
            # First, try to get max generation from moves with game states
            if moves:
                generations_from_moves = []
                for move in moves:
                    if move.game_state and move.game_state.generation:
                        generations_from_moves.append(move.game_state.generation)
                
                if generations_from_moves:
                    max_generation = max(generations_from_moves)
                    logger.info(f"Found max generation {max_generation} from moves")
                    return max_generation
            
            # Fallback: try to extract from vp_progression data
            # This is less reliable but can be used if moves don't have generation data
            if vp_progression:
                # VP progression entries might contain generation information
                # This would need to be implemented based on the actual structure
                logger.info("Attempting to extract generation from vp_progression (fallback)")
                # For now, we'll use a simple heuristic based on the number of VP entries
                # In Terraforming Mars, games typically last 8-12 generations
                estimated_generations = min(12, max(8, len(vp_progression) // 2))
                max_generation = estimated_generations
                logger.info(f"Estimated max generation {max_generation} from vp_progression length")
            
        except Exception as e:
            logger.error(f"Error calculating max generation: {e}")
            max_generation = 1
        
        logger.info(f"Calculated max generation: {max_generation}")
        return max_generation

    def _extract_metadata(self, soup: BeautifulSoup, html_content: str, moves: List[Move]) -> Dict[str, Any]:
        """Extract metadata about the parsing process"""
        # Calculate total moves as the maximum move_number
        total_moves = 0
        if moves:
            total_moves = max(move.move_number for move in moves)
        
        return {
            'parsed_at': datetime.now().isoformat(),
            'total_moves': total_moves
        }

    def _extract_tracker_dictionary_from_html(self, html_content: str) -> Dict[str, str]:
        """Dynamically extract all tracker mappings from HTML elements"""
        tracker_dict = {}
        
        try:
            logger.info("Starting tracker dictionary extraction...")
            
            # Method 1: Look for elements with data-name attributes
            patterns = [
                # Look for data-name attribute
                r'<[^>]*id="((?:tracker_|counter_)[^"]+)"[^>]*data-name="([^"]+)"[^>]*>',
                # Look for title attribute  
                r'<[^>]*id="((?:tracker_|counter_)[^"]+)"[^>]*title="([^"]+)"[^>]*>',
            ]
            
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                logger.info(f"Pattern {i+1} found {len(matches)} matches")
                
                for tracker_id, display_name in matches:
                    if tracker_id and display_name:
                        tracker_dict[tracker_id] = display_name.strip()
            
            # Method 2: If we didn't get enough results, try aggressive extraction
            if len(tracker_dict) < 10:  # Expect more trackers in a typical game
                logger.info("Not enough trackers found, trying aggressive extraction...")
                
                # Find all tracker/counter IDs first
                id_pattern = r'id="((?:tracker_|counter_)[^"]+)"'
                all_ids = re.findall(id_pattern, html_content, re.IGNORECASE)
                logger.info(f"Found {len(all_ids)} tracker/counter IDs total")
                
                for tracker_id in all_ids:
                    if tracker_id not in tracker_dict:
                        # Try to find the display name by looking at the surrounding HTML
                        display_name = self._infer_display_name_from_context(tracker_id, html_content)
                        if display_name:
                            tracker_dict[tracker_id] = display_name
            
            logger.info(f"Extracted {len(tracker_dict)} tracker mappings dynamically from HTML")
            
            # Log some examples for debugging
            if tracker_dict:
                sample_items = list(tracker_dict.items())[:5]
                logger.info(f"Sample tracker mappings: {sample_items}")
            
            return tracker_dict
            
        except Exception as e:
            logger.error(f"Error extracting tracker dictionary: {e}")
            return {}

    def _infer_display_name_from_context(self, tracker_id: str, html_content: str) -> str:
        """Try to infer display name from surrounding HTML context"""
        try:
            # Find the tracker element in the HTML
            tracker_pattern = rf'id="{re.escape(tracker_id)}"'
            match = re.search(tracker_pattern, html_content)
            
            if not match:
                return ""
            
            # Extract surrounding context (1000 chars before and after)
            start = max(0, match.start() - 1000)
            end = min(len(html_content), match.end() + 1000)
            context = html_content[start:end]
            
            # Look for data-name or title attributes in the context
            name_patterns = [
                rf'id="{re.escape(tracker_id)}"[^>]*data-name="([^"]+)"',
                rf'id="{re.escape(tracker_id)}"[^>]*title="([^"]+)"',
                rf'data-name="([^"]+)"[^>]*id="{re.escape(tracker_id)}"',
                rf'title="([^"]+)"[^>]*id="{re.escape(tracker_id)}"',
            ]
            
            for pattern in name_patterns:
                name_match = re.search(pattern, context, re.IGNORECASE)
                if name_match:
                    return name_match.group(1).strip()
            
            # If no explicit name found, try to infer from the tracker ID itself
            return self._infer_from_tracker_id(tracker_id)
            
        except Exception as e:
            logger.error(f"Error inferring display name for {tracker_id}: {e}")
            return ""

    def _infer_from_tracker_id(self, tracker_id: str) -> str:
        """Infer display name from tracker ID patterns"""
        # Remove player color code (6-digit hex at the end)
        base_id = re.sub(r'_[a-f0-9]{6}$', '', tracker_id, flags=re.IGNORECASE)
        
        # Map common tracker patterns to display names
        mappings = {
            'counter_hand': 'Hand Counter',
            'tracker_m': 'MC',
            'tracker_pm': 'MC Production',
            'tracker_s': 'Steel',
            'tracker_ps': 'Steel Production',
            'tracker_u': 'Titanium',
            'tracker_pu': 'Titanium Production',
            'tracker_p': 'Plant',
            'tracker_pp': 'Plant Production',
            'tracker_e': 'Energy',
            'tracker_pe': 'Energy Production',
            'tracker_h': 'Heat',
            'tracker_ph': 'Heat Production',
            'tracker_tagBuilding': 'Count of Building tags',
            'tracker_tagSpace': 'Count of Space tags',
            'tracker_tagScience': 'Count of Science tags',
            'tracker_tagEnergy': 'Count of Power tags',
            'tracker_tagEarth': 'Count of Earth tags',
            'tracker_tagJovian': 'Count of Jovian tags',
            'tracker_tagCity': 'Count of City tags',
            'tracker_tagPlant': 'Count of Plant tags',
            'tracker_tagMicrobe': 'Count of Microbe tags',
            'tracker_tagAnimal': 'Count of Animal tags',
            'tracker_tagWild': 'Count of Wild tags',
            'tracker_tagEvent': 'Count of played Events cards'
        }
        
        return mappings.get(base_id, f"Unknown ({base_id})")

    def _track_resources_and_production(self, gamelogs: Dict[str, Any], player_ids: List[str], 
                                       tracker_dict: Dict[str, str]) -> List[Dict[str, Any]]:
        """Track comprehensive player state through all moves using gamelogs JSON"""
        logger.info(f"Starting comprehensive tracking for {len(player_ids)} players")
        logger.info(f"Tracker dictionary has {len(tracker_dict)} mappings")
        
        try:
            # Initialize tracking data with actual player IDs and only player-specific trackers
            player_data = {}
            
            # Filter tracker_dict to only include player-specific trackers (those with color codes)
            player_specific_trackers = {}
            for tracker_id, display_name in tracker_dict.items():
                # Check if tracker ID ends with a 6-character hex color code
                if re.search(r'_[a-f0-9]{6}$', tracker_id, re.IGNORECASE):
                    player_specific_trackers[tracker_id] = display_name
            
            logger.info(f"Found {len(player_specific_trackers)} player-specific trackers out of {len(tracker_dict)} total")
            
            # Get unique display names from player-specific trackers only
            player_tracker_names = set(player_specific_trackers.values())
            
            # Also filter out global trackers by name patterns
            global_tracker_patterns = [
                'Temperature', 'Oxygen Level', 'Oceans', 'TR', 'Global Parameters Delta',
                'Number of Greenery on Mars', 'Number of owned land', 'Number of Cities',
                'Number of Cities on Mars', 'Pass', 'Steel Exchange Rate', 'Titanium Exchange Rate'
            ]
            
            # Remove global trackers from player tracker names
            filtered_tracker_names = set()
            for tracker_name in player_tracker_names:
                is_global = False
                for pattern in global_tracker_patterns:
                    if pattern in tracker_name:
                        is_global = True
                        break
                if not is_global:
                    filtered_tracker_names.add(tracker_name)
            
            player_tracker_names = filtered_tracker_names
            logger.info(f"After filtering global trackers: {len(player_tracker_names)} player-specific tracker names")
            
            for player_id in player_ids:
                # Initialize all trackers to 0
                player_trackers = {tracker_name: 0 for tracker_name in player_tracker_names}
                player_data[int(player_id)] = player_trackers
            
            logger.info(f"Initialized {len(player_tracker_names)} player-specific trackers for each player")
            
            tracking_progression = []
            
            # Get all moves from gamelogs
            data_entries = gamelogs.get('data', {}).get('data', [])
            if not data_entries:
                logger.warning("No data entries found in gamelogs")
                return []
            
            # Find the maximum move ID to determine range
            max_move_id = 0
            for entry in data_entries:
                move_id = entry.get('move_id')
                if move_id and str(move_id).isdigit():
                    max_move_id = max(max_move_id, int(move_id))
            
            logger.info(f"Processing {max_move_id} moves for tracking")
            
            # Process each move
            for move_index in range(1, max_move_id + 1):
                # Find the move entry
                move_entry = None
                for entry in data_entries:
                    if entry.get('move_id') == str(move_index):
                        move_entry = entry
                        break
                
                if not move_entry:
                    # Even if no move entry, store current state to maintain progression
                    tracking_entry = {
                        'move_number': move_index,
                        'data': {pid: dict(data) for pid, data in player_data.items()}
                    }
                    tracking_progression.append(tracking_entry)
                    continue
                
                # Process all submoves in this move to find counter updates
                submoves = move_entry.get('data', [])
                for submove in submoves:
                    if not isinstance(submove, dict):
                        continue
                    
                    # Look for counter updates
                    args = submove.get('args', {})
                    if 'counter_name' in args and 'counter_value' in args and 'player_id' in args:
                        counter_name = args['counter_name']
                        counter_value = args['counter_value']
                        gamelogs_player_id = str(args['player_id'])
                        
                        # Find the display name for this counter
                        display_name = tracker_dict.get(counter_name)
                        if display_name:
                            # Check if this tracker should be excluded (same logic as initialization)
                            global_tracker_patterns = [
                                'Temperature', 'Oxygen Level', 'Oceans', 'TR', 'Global Parameters Delta',
                                'Number of Greenery on Mars', 'Number of owned land', 'Number of Cities',
                                'Number of Cities on Mars', 'Pass', 'Steel Exchange Rate', 'Titanium Exchange Rate'
                            ]
                            
                            # Skip if this is a global tracker that should be excluded
                            is_global = False
                            for pattern in global_tracker_patterns:
                                if pattern in display_name:
                                    is_global = True
                                    break
                            
                            if is_global:
                                logger.debug(f"Move {move_index}: Skipping global tracker {display_name}")
                                continue
                            
                            # Convert gamelogs player ID to actual player ID
                            actual_player_id = int(gamelogs_player_id)
                            
                            if actual_player_id in player_data:
                                # Convert value to int and update the persistent state
                                try:
                                    validated_value = int(counter_value)
                                except (ValueError, TypeError):
                                    validated_value = 0
                                
                                # Only update if this tracker exists in player_data (was initialized)
                                if display_name in player_data[actual_player_id]:
                                    player_data[actual_player_id][display_name] = validated_value
                                    logger.debug(f"Move {move_index}: Player {actual_player_id} {display_name} = {validated_value}")
                                else:
                                    logger.debug(f"Move {move_index}: Skipping uninitialized tracker {display_name}")
                
                # Store snapshot of current state (includes all previous values + any updates from this move)
                tracking_entry = {
                    'move_number': move_index,
                    'data': {pid: dict(data) for pid, data in player_data.items()}
                }
                tracking_progression.append(tracking_entry)
            
            logger.info(f"Completed tracking: {len(tracking_progression)} move snapshots")
            return tracking_progression
            
        except Exception as e:
            logger.error(f"Error in comprehensive tracking: {e}")
            return []

    def _update_game_states_with_tracking(self, moves: List[Move], tracking_progression: List[Dict[str, Any]]):
        """Update GameState objects with comprehensive tracking data"""
        logger.info(f"Updating {len(moves)} game states with tracking data")
        
        # Create a mapping from move number to tracking data
        tracking_by_move = {}
        for entry in tracking_progression:
            move_number = entry['move_number']
            tracking_by_move[move_number] = entry['data']
        
        # Update each move's game state
        for move in moves:
            if not move.game_state:
                continue
            
            # Get tracking data for this move
            move_tracking = tracking_by_move.get(move.move_number, {})
            
            if move_tracking:
                # Store tracking data directly without categorization
                for player_id, player_tracking in move_tracking.items():
                    # Convert player_id to string for consistent key usage
                    player_id_str = str(player_id)
                    
                    # Initialize player trackers if not present
                    if player_id_str not in move.game_state.player_trackers:
                        move.game_state.player_trackers[player_id_str] = {}
                    
                    # Store all tracker values directly
                    for tracker_name, value in player_tracking.items():
                        # Convert value to int and store directly with original tracker name
                        try:
                            validated_value = int(value)
                        except (ValueError, TypeError):
                            validated_value = 0
                        
                        move.game_state.player_trackers[player_id_str][tracker_name] = validated_value
                
                logger.debug(f"Updated game state for move {move.move_number} with tracking data")
        
        logger.info("Completed updating game states with comprehensive tracking data")

    def parse_complete_game_with_elo(self, replay_html: str, table_html: str, table_id: str, player_perspective: str) -> GameData:
        """Parse a complete game with ELO data from both replay and table HTML (legacy method for backward compatibility)"""
        logger.info(f"Starting parsing with ELO data for game {table_id} (legacy method)")
        
        # Parse table metadata first
        game_metadata = self.parse_table_metadata(table_html)
        
        game_data = self.parse_complete_game(
            replay_html=replay_html,
            game_metadata=game_metadata,
            table_id=table_id,
            player_perspective=player_perspective
        )
        
        # Update metadata to indicate ELO data was included (for backward compatibility)
        if game_metadata.players:
            game_data.metadata['elo_data_included'] = len(game_metadata.players) > 0
            game_data.metadata['elo_players_found'] = len(game_metadata.players)
        
        logger.info(f"Legacy parsing with ELO complete for game {table_id}")
        return game_data
    
    def parse_elo_data(self, table_html: str) -> Dict[str, EloData]:
        """
        Parse ELO data from table page HTML
        
        Args:
            table_html: HTML content of the table page
            
        Returns:
            dict: Player name -> EloData mapping
        """
        logger.info("Parsing ELO data from table HTML")
        
        soup = BeautifulSoup(table_html, 'html.parser')
        elo_data = {}
        
        try:
            # Use score-entry sections which contain complete player data
            score_entries = soup.find_all('div', class_='score-entry')
            logger.info(f"Found {len(score_entries)} score entries")
            
            for entry in score_entries:
                player_elo = self._parse_player_from_score_entry(entry)
                if player_elo and 'player_name' in player_elo:
                    player_name = player_elo['player_name']  # Don't pop, keep it in the dict
                    elo_data[player_name] = EloData(**player_elo)
                    logger.info(f"Parsed ELO data for {player_name}")
            
            logger.info(f"Successfully parsed ELO data for {len(elo_data)} players")
            return elo_data
            
        except Exception as e:
            logger.error(f"Error parsing ELO data: {e}")
            return {}
    
    def parse_game_mode(self, table_html: str) -> str:
        
        soup = BeautifulSoup(table_html, 'html.parser')

        span_element = soup.find('span', id='mob_gameoption_201_displayed_value')

        if span_element:

            mode = span_element.get_text().strip()

            return mode
        
        else:
            return "Normal mode" # Default
    
    def _parse_player_from_score_entry(self, score_entry: Tag) -> Optional[Dict[str, Any]]:
        """Parse ELO data for a single player from their score entry section"""
        try:
            player_data = {}
            
            # Extract player name from playername link
            player_link = score_entry.find('a', class_='playername')
            if player_link:
                player_data['player_name'] = player_link.get_text().strip()

            # Extract player ID from href attribute
            href = player_link.get('href')
            if href:
                # Extract ID from "/player?id=86296239" format
                id_match = re.search(r'id=(\d+)', href)
                if id_match:
                    player_data['player_id'] = id_match.group(1)

            # Extract position from rank div
            rank_div = score_entry.find('div', class_='rank')
            if rank_div:
                rank_text = rank_div.get_text().strip()
                # Extract number from "1st", "2nd", "3rd", etc.
                position_match = re.search(r'(\d+)', rank_text)
                if position_match:
                    player_data['position'] = int(position_match.group(1))

            # Extract ELO rating from gamerank_value span
            elo_span = score_entry.find('span', class_='gamerank_value')
            if elo_span:
                elo_text = elo_span.get_text().strip()
                try:
                    player_data['game_rank'] = int(elo_text)
                except ValueError:
                    # In case the ELO text isn't a valid integer
                    player_data['game_rank'] = None
            else:
                player_data['game_rank'] = None

            
            # Find all winpoints in this entry (there should be 2: arena and regular)
            winpoints = score_entry.find_all('div', class_='winpoints')
            
            # Find all newrank in this entry (there should be 2: arena and regular)
            newranks = score_entry.find_all('div', class_='newrank')
            
            # Parse Arena data (first winpoints/newrank pair)
            if len(winpoints) >= 1:
                arena_winpoints_text = winpoints[0].get_text().strip()
                # Extract arena points change
                arena_change_match = re.search(r'([+-]\d+)', arena_winpoints_text)
                if arena_change_match:
                    player_data['arena_points_change'] = int(arena_change_match.group(1))
            
            if len(newranks) >= 1:
                arena_newrank_text = newranks[0].get_text().strip()
                # Extract arena points (current)
                arena_points_match = re.search(r'(\d+)\s*pts', arena_newrank_text)
                if arena_points_match:
                    player_data['arena_points'] = int(arena_points_match.group(1))
            
            # Parse Game ELO data (second winpoints/newrank pair)
            if len(winpoints) >= 2:
                game_winpoints_text = winpoints[1].get_text().strip()
                # Extract game ELO change
                game_change_match = re.search(r'([+-]\d+)', game_winpoints_text)
                if game_change_match:
                    player_data['game_rank_change'] = int(game_change_match.group(1))        
            
            logger.info(f"Extracted ELO data for {player_data['player_name']}: {player_data}")
            return player_data if len(player_data) > 1 else None  # Must have more than just player_name
            
        except Exception as e:
            logger.error(f"Error parsing player from score entry: {e}")
            return None

    def _merge_elo_with_players(self, players: Dict[str, Player], elo_data: Dict[str, EloData]):
        """Merge ELO data into player objects"""
        logger.info(f"Merging ELO data for {len(elo_data)} players")
        
        for player_id, player in players.items():
            # Try to find ELO data by player name
            if player.player_name in elo_data:
                player.elo_data = elo_data[player.player_name]
                logger.info(f"Merged ELO data for player {player.player_name}")
            else:
                logger.warning(f"No ELO data found for player {player.player_name}")

    def parse_replay_with_assignment_metadata(self, replay_html: str, assignment_metadata: Dict[str, Any], table_id: str, player_perspective: str) -> Dict[str, Any]:
        """
        Parse replay HTML combined with assignment metadata (for replay scraping assignments)
        This method uses the ELO data and player info from the assignment instead of scraping table HTML
        
        Args:
            replay_html: HTML content from replay page
            assignment_metadata: Assignment data containing ELO info, player data, etc.
            table_id: BGA table ID
            player_perspective: Player ID whose perspective this is from
            
        Returns:
            dict: Complete parsed game data ready for API upload
        """
        try:
            logger.info(f"Parsing replay with assignment metadata for game {table_id}")
            
            # Convert assignment metadata to GameMetadata format
            game_metadata = self.convert_assignment_to_game_metadata(assignment_metadata)
            
            # Use unified parsing method
            game_data = self.parse_complete_game(
                replay_html=replay_html,
                game_metadata=game_metadata,
                table_id=table_id,
                player_perspective=player_perspective
            )
            
            # Add assignment metadata to game data metadata
            game_data.metadata['assignment_metadata_used'] = True
            game_data.metadata['elo_data_included'] = len(game_metadata.players) > 0 if game_metadata.players else False
            game_data.metadata['elo_players_found'] = len(game_metadata.players) if game_metadata.players else 0
            game_data.metadata['parsed_at'] = datetime.now().isoformat()
            
            # Convert to dictionary format for API upload
            result = self._convert_game_data_to_api_format(game_data, table_id, player_perspective)
            
            logger.info(f"Successfully parsed replay with assignment metadata for game {table_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing replay with assignment metadata for {table_id}: {e}")
            return {}

    def _create_players_from_assignment_metadata(self, elo_data: Dict[str, EloData], assignment_metadata: Dict[str, Any], replay_html: str, table_id: str) -> Dict[str, Player]:
        """Create player objects from assignment metadata"""
        logger.info(f"Creating players from assignment metadata for {len(elo_data)} players")
        
        players = {}
        soup = BeautifulSoup(replay_html, 'html.parser')
        
        # Get VP data for final scores
        vp_data = self._extract_vp_data_from_html(replay_html)
        
        # Get corporations from replay HTML
        corporations = self._extract_corporations(soup)
        
        for player_name, elo_info in elo_data.items():
            player_id = elo_info.player_id
            
            # Get final VP and breakdown
            final_vp = 0
            vp_breakdown = {}
            if player_id in vp_data:
                final_vp = vp_data[player_id].get('total', 0)
                vp_breakdown = vp_data[player_id].get('total_details', {})
            
            # Create player object
            player = Player(
                player_id=player_id,
                player_name=player_name,
                corporation=corporations.get(player_name, 'Unknown'),
                final_vp=final_vp,
                final_tr=vp_breakdown.get('tr', 20),
                vp_breakdown=vp_breakdown,
                cards_played=[],  # Will be populated from moves
                milestones_claimed=[],  # Will be populated from moves
                awards_funded=[],  # Will be populated from moves
                elo_data=elo_info
            )
            
            players[player_id] = player
            logger.info(f"Created player {player_name} with ID {player_id}")
        
        return players

    def _convert_game_data_to_api_format(self, game_data: GameData, table_id: str, player_perspective: str) -> Dict[str, Any]:
        """Convert GameData object to format expected by StoreGameLog API"""
        try:
            # Convert dataclasses to dictionaries for JSON serialization
            def convert_to_dict(obj):
                if hasattr(obj, '__dict__'):
                    return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
                elif isinstance(obj, list):
                    return [convert_to_dict(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: convert_to_dict(v) for k, v in obj.items()}
                else:
                    return obj
            
            # Convert the entire game data to dictionary
            result = convert_to_dict(game_data)
            
            # Ensure required fields are present
            result['table_id'] = table_id
            result['player_perspective'] = player_perspective
            
            logger.info(f"Converted game data to API format for {table_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error converting game data to API format: {e}")
            return {}

    def _extract_all_moves_simple(self, soup: BeautifulSoup, name_to_id: Dict[str, str], gamelogs: Dict[str, Any] = None) -> List[Move]:
        """Extract all moves with simple name-to-ID mapping"""
        moves = []
        move_divs = soup.find_all('div', class_='replaylogs_move')
        
        for move_div in move_divs:
            move = self._parse_single_move_detailed(move_div, name_to_id, gamelogs)
            if move:
                moves.append(move)
        
        return moves

    def _build_game_states_simple(self, moves: List[Move], vp_progression: List[Dict[str, Any]], player_ids: List[str], gamelogs: Dict[str, Any] = None) -> List[Move]:
        """Build game states for each move with simple player ID list"""
        # Initialize tracking variables
        current_temp = -30
        current_oxygen = 0
        current_oceans = 0
        current_generation = 1
        
        # Track milestones and awards state throughout the game
        current_milestones = {}
        current_awards = {}
        
        # Initialize default VP data for all players
        default_vp_data = {}
        for player_id in player_ids:
            default_vp_data[player_id] = {
                "total": 20,
                "total_details": {
                    "tr": 20,
                    "awards": 0,
                    "milestones": 0,
                    "cities": 0,
                    "greeneries": 0,
                    "cards": 0
                }
            }
        
        # Track the last known VP data to carry forward when no new data is available
        last_vp_data = dict(default_vp_data)
        
        # Create a mapping from move_number to VP data for proper correlation
        vp_by_move_number = {}
        for vp_entry in vp_progression:
            move_number = vp_entry.get('move_number')
            if move_number:
                # Convert move_number to string for consistent matching
                vp_by_move_number[str(move_number)] = vp_entry.get('vp_data', {})
        
        logger.info(f"Built VP mapping for {len(vp_by_move_number)} moves")
        
        # Extract parameter changes from gamelogs if available
        parameter_changes_by_move = {}
        if gamelogs:
            parameter_changes_by_move = self._extract_parameter_changes_from_gamelogs(gamelogs)
            logger.info(f"Extracted parameter changes for {len(parameter_changes_by_move)} moves from gamelogs")
        
        # Process each move and build game state
        for i, move in enumerate(moves):
            # Update generation
            if 'New generation' in move.description:
                gen_match = re.search(r'New generation (\d+)', move.description)
                if gen_match:
                    current_generation = int(gen_match.group(1))
            
            # Update parameters from gamelogs data
            move_parameter_changes = parameter_changes_by_move.get(move.move_number, {})
            if move_parameter_changes:
                if 'temperature' in move_parameter_changes:
                    current_temp = move_parameter_changes['temperature']
                    logger.debug(f"Move {move.move_number}: Temperature updated to {current_temp}")
                if 'oxygen' in move_parameter_changes:
                    current_oxygen = move_parameter_changes['oxygen']
                    logger.debug(f"Move {move.move_number}: Oxygen updated to {current_oxygen}")
                if 'oceans' in move_parameter_changes:
                    current_oceans = move_parameter_changes['oceans']
                    logger.debug(f"Move {move.move_number}: Oceans updated to {current_oceans}")
            
            # Update milestone and award tracking
            if move.action_type == 'claim_milestone':
                milestone_match = re.search(r'claims milestone (\w+)', move.description)
                if milestone_match:
                    milestone_name = milestone_match.group(1)
                    current_milestones[milestone_name] = {
                        'claimed_by': move.player_name,
                        'player_id': move.player_id,
                        'move_number': move.move_number,
                        'timestamp': move.timestamp
                    }
            
            if move.action_type == 'fund_award':
                award_match = re.search(r'funds (\w+) award', move.description)
                if award_match:
                    award_name = award_match.group(1)
                    current_awards[award_name] = {
                        'funded_by': move.player_name,
                        'player_id': move.player_id,
                        'move_number': move.move_number,
                        'timestamp': move.timestamp
                    }
            
            # Get VP data for this move by matching move_number
            move_vp_data = vp_by_move_number.get(str(move.move_number), {})
            
            # Ensure VP data is always present
            if move_vp_data:
                # Update last known VP data with new data
                last_vp_data = dict(move_vp_data)
                logger.debug(f"Updated VP data for move {move.move_number}")
            else:
                # Use last known VP data if no new data available
                move_vp_data = dict(last_vp_data)
                logger.debug(f"Using carried-forward VP data for move {move.move_number}")
            
            # Ensure all players have VP data (fill in missing players with defaults)
            for player_id in player_ids:
                if player_id not in move_vp_data:
                    move_vp_data[player_id] = dict(default_vp_data[player_id])
                    logger.debug(f"Added default VP data for missing player {player_id} in move {move.move_number}")
            
            # Create game state (without resource/production tracking)
            game_state = GameState(
                move_number=move.move_number,
                generation=current_generation,
                temperature=current_temp,
                oxygen=current_oxygen,
                oceans=current_oceans,
                player_vp=move_vp_data,
                milestones=dict(current_milestones),
                awards=dict(current_awards)
            )
            
            move.game_state = game_state
        
        return moves

    def _determine_winner_from_game_states(self, moves_with_states: List[Move], players_info: Dict[str, Player]) -> str:
        """Determine winner from final game state VP data"""
        if not moves_with_states or not players_info:
            return "Unknown"
        
        # Get final VP data from the last move with game state
        final_vp_data = {}
        for move in reversed(moves_with_states):
            if move.game_state and move.game_state.player_vp:
                final_vp_data = move.game_state.player_vp
                break
        
        if not final_vp_data:
            # Fallback to player info
            max_vp = max(player.final_vp for player in players_info.values())
            winners = [player.player_name for player in players_info.values() if player.final_vp == max_vp]
            return winners[0] if winners else "Unknown"
        
        # Find player with highest VP
        max_vp = 0
        winner_id = None
        
        for player_id, vp_data in final_vp_data.items():
            total_vp = vp_data.get('total', 0)
            if total_vp > max_vp:
                max_vp = total_vp
                winner_id = player_id
        
        # Convert player ID to player name
        if winner_id and winner_id in players_info:
            return players_info[winner_id].player_name
        
        return "Unknown"

    def export_to_json(self, game_data: GameData, output_path: str, player_perspective: str = None):
        """Export game data to JSON with player perspective folder structure"""
        # If player_perspective is provided, modify the output path to include it
        if player_perspective:
            # Extract directory and filename
            dir_path = os.path.dirname(output_path)
            filename = os.path.basename(output_path)
            
            # Create player perspective subdirectory
            player_dir = os.path.join(dir_path, player_perspective)
            output_path = os.path.join(player_dir, filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convert dataclasses to dictionaries for JSON serialization
        def convert_to_dict(obj):
            if hasattr(obj, '__dict__'):
                return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [convert_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_to_dict(v) for k, v in obj.items()}
            else:
                return obj
        
        data_dict = convert_to_dict(game_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
