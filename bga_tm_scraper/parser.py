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
    card_cost: Optional[int] = None
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
    
    # Players
    players: Dict[str, Player]  # player_id -> Player
    
    # All moves with game states
    moves: List[Move]
    
    # Final game state
    final_state: GameState
    
    # Game progression data
    parameter_progression: List[Dict[str, Any]]
    
    # Analysis metadata
    metadata: Dict[str, Any]

class Parser:
    """Comprehensive Terraforming Mars game log parser for BoardGameArena replays"""
    
    def __init__(self):
        pass
    
    def parse_complete_game(self, html_content: str, replay_id: str, player_perspective: str) -> GameData:
        """Parse a complete game and return comprehensive data structure"""
        logger.info(f"Starting parsing for game {replay_id}")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract gamelogs once for memory efficiency
        gamelogs = self._extract_g_gamelogs(html_content)
        
        # Extract basic game info
        players_info = self._extract_players_info(soup, html_content)
        
        # Extract all moves with detailed parsing
        moves = self._extract_all_moves(soup, players_info, gamelogs)
        
        # Extract VP progression throughout the game
        vp_progression = self._extract_vp_progression(html_content)
        
        # Build game states for each move
        moves_with_states = self._build_game_states(moves, vp_progression, players_info, gamelogs)
        
        # Add comprehensive resource/production/tag tracking if gamelogs available
        tracking_progression = []
        if gamelogs and players_info:
            logger.info("Adding comprehensive tracking data to game states")
            # Extract tracker dictionary dynamically from HTML
            tracker_dict = self._extract_tracker_dictionary_from_html(html_content)
            
            # Get player IDs for tracking
            player_ids = list(players_info.keys())
            
            # Track resources and production through all moves
            tracking_progression = self._track_resources_and_production(gamelogs, player_ids, tracker_dict)
            
            # Update game states with tracking data
            self._update_game_states_with_tracking(moves_with_states, tracking_progression)
        
        # Extract parameter progression
        parameter_progression = self._extract_parameter_progression(moves_with_states)
        
        # Build final game state
        final_state = moves_with_states[-1].game_state if moves_with_states else GameState(
            move_number=0, generation=1, temperature=-30, oxygen=0, oceans=0,
            player_vp={}, milestones={}, awards={}
        )
        
        # Determine winner
        winner = self._determine_winner(players_info)
        
        # Extract game metadata
        metadata = self._extract_metadata(soup, html_content, moves_with_states)
        
        # Calculate max generation from vp_progression or moves
        max_generation = self._calculate_max_generation(vp_progression, moves_with_states)
        
        # Create game data
        game_data = GameData(
            replay_id=replay_id,
            player_perspective=player_perspective,
            game_date=self._extract_game_date(soup),
            game_duration=self._calculate_game_duration(moves_with_states),
            winner=winner,
            generations=max_generation,
            players=players_info,
            moves=moves_with_states,
            final_state=final_state,
            parameter_progression=parameter_progression,
            metadata=metadata
        )
        
        logger.info(f"Parsing complete for game {replay_id}: {len(moves_with_states)} moves, {len(players_info)} players")
        return game_data
    
    def _extract_players_info(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Player]:
        """Extract comprehensive player information using gamelogs-first approach"""
        # First, try to get player names from gamelogs (most reliable)
        gamelogs = self._extract_g_gamelogs(html_content)
        vp_data = self._extract_vp_data_from_html(html_content)
        valid_player_ids = set(vp_data.keys())
        
        player_names = []
        player_id_map = {}
        
        if gamelogs and valid_player_ids:
            logger.info("Extracting player info using gamelogs-first approach")
            # Extract player mapping directly from gamelogs
            gamelogs_mapping = self._extract_player_mapping_from_gamelogs(gamelogs, valid_player_ids)
            if gamelogs_mapping:
                logger.info(f"Found complete gamelogs mapping: {gamelogs_mapping}")
                player_names = list(gamelogs_mapping.keys())
                player_id_map = gamelogs_mapping
        
        # Fallback: Get player names from HTML span elements if gamelogs approach failed
        if not player_names:
            logger.info("Gamelogs approach failed, falling back to HTML span extraction")
            player_elements = soup.find_all('span', class_='playername')
            for elem in player_elements:
                player_name = elem.get_text().strip()
                if player_name and player_name not in player_names:
                    player_names.append(player_name)
            
            # Get player ID mapping using the improved method
            if player_names:
                player_id_map = self._extract_player_id_mapping(html_content, player_names)
        
        # Final fallback: Extract player names from move descriptions
        if not player_names:
            logger.info("No playername spans found, extracting from move descriptions")
            player_names = self._extract_player_names_from_moves(soup)
            if player_names:
                player_id_map = self._extract_player_id_mapping(html_content, player_names)
        
        # Get corporations
        corporations = self._extract_corporations(soup)
        
        # Build player objects
        players = {}
        for player_name in player_names:
            player_id = player_id_map.get(player_name, f"unknown_{len(players)}")
            
            # Get final VP and breakdown
            final_vp = 0
            vp_breakdown = {}
            if player_id in vp_data:
                final_vp = vp_data[player_id].get('total', 0)
                vp_breakdown = vp_data[player_id].get('total_details', {})
            
            players[player_id] = Player(
                player_id=player_id,
                player_name=player_name,
                corporation=corporations.get(player_name, 'Unknown'),
                final_vp=final_vp,
                final_tr=vp_breakdown.get('tr', 20),
                vp_breakdown=vp_breakdown,
                cards_played=[],  # Will be populated from moves
                milestones_claimed=[],  # Will be populated from moves
                awards_funded=[]  # Will be populated from moves
            )
        
        logger.info(f"Extracted {len(players)} players using gamelogs-first approach: {list(players.keys())}")
        return players
    
    def _extract_player_names_from_moves(self, soup: BeautifulSoup) -> List[str]:
        """Extract player names from move descriptions as fallback"""
        player_names = set()
        
        # Look for player names in move descriptions
        log_entries = soup.find_all('div', class_='gamelogreview')
        for entry in log_entries:
            text = entry.get_text()
            
            # Look for patterns like "PlayerName plays card", "PlayerName chooses corporation", etc.
            patterns = [
                r'(\w+(?:\s+\w+)*) plays card',
                r'(\w+(?:\s+\w+)*) chooses corporation',
                r'(\w+(?:\s+\w+)*) gains',
                r'(\w+(?:\s+\w+)*) pays',
                r'(\w+(?:\s+\w+)*) increases',
                r'(\w+(?:\s+\w+)*) places',
                r'(\w+(?:\s+\w+)*) claims milestone',
                r'(\w+(?:\s+\w+)*) funds.*award'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Clean up the match and add if it looks like a player name
                    name = match.strip()
                    if name and len(name) > 1 and name not in ['You', 'Module', 'Map']:
                        player_names.add(name)
        
        result = list(player_names)
        logger.info(f"Extracted {len(result)} player names from moves: {result}")
        return result
    
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
            card_cost = self._extract_card_cost(log_entries)
            tile_placed, tile_location = self._extract_tile_placement(log_entries)
            
            move = Move(
                move_number=move_number,
                timestamp=timestamp,
                player_id=player_id,
                player_name=player_name,
                action_type=action_type,
                description=full_description,
                card_played=card_played,
                card_cost=card_cost,
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
    
    def _extract_card_cost(self, log_entries: List[Tag]) -> Optional[int]:
        """Extract the cost of the card played"""
        for entry in log_entries:
            text = entry.get_text()
            if 'pays' in text and 'M€' in text:
                # Look for cost pattern
                cost_match = re.search(r'pays (\d+)', text)
                if cost_match:
                    return int(cost_match.group(1))
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
    
    def _extract_resource_changes_detailed(self, log_entries: List[Tag]) -> Dict[str, int]:
        """Extract detailed resource changes"""
        changes = {}
        
        for entry in log_entries:
            html_content = str(entry)
            
            # Pattern for gains/pays with number before resource
            gain_pattern = r'gains (\d+) <div class="token_img tracker_(\w+)"[^>]*title="([^"]*)"[^>]*></div>'
            pay_pattern = r'pays (\d+) <div class="token_img tracker_(\w+)"[^>]*title="([^"]*)"[^>]*></div>'
            
            # Pattern for gains/pays with number after resource
            gain_after_pattern = r'gains <div class="token_img tracker_(\w+)"[^>]*title="([^"]*)"[^>]*></div>(\d+)'
            pay_after_pattern = r'pays <div class="token_img tracker_(\w+)"[^>]*title="([^"]*)"[^>]*></div>(\d+)'
            
            patterns = [
                (gain_pattern, 1),
                (pay_pattern, -1),
                (gain_after_pattern, 1),
                (pay_after_pattern, -1)
            ]
            
            for pattern, sign in patterns:
                matches = re.finditer(pattern, html_content)
                for match in matches:
                    if pattern in [gain_pattern, pay_pattern]:
                        amount = int(match.group(1)) * sign
                        tracker = match.group(2)
                        title = match.group(3)
                    else:
                        tracker = match.group(1)
                        title = match.group(2)
                        amount = int(match.group(3)) * sign
                    
                    resource_name = self._map_tracker_to_resource(tracker, title)
                    if 'Production' not in title:  # Only count non-production changes here
                        changes[resource_name] = changes.get(resource_name, 0) + amount
        
        return changes
    
    def _extract_production_changes_detailed(self, log_entries: List[Tag]) -> Dict[str, int]:
        """Extract detailed production changes"""
        changes = {}
        
        for entry in log_entries:
            html_content = str(entry)
            
            # Production increase/decrease patterns
            increase_prod_pattern = r'increases <div class="token_img tracker_(\w+)"[^>]*title="([^"]*)"[^>]*></div> by (\d+)'
            reduce_prod_pattern = r'reduces <div class="token_img tracker_(\w+)"[^>]*title="([^"]*)"[^>]*></div> by (\d+)'
            
            patterns = [
                (increase_prod_pattern, 1),
                (reduce_prod_pattern, -1)
            ]
            
            for pattern, sign in patterns:
                matches = re.finditer(pattern, html_content)
                for match in matches:
                    tracker = match.group(1)
                    title = match.group(2)
                    amount = int(match.group(3)) * sign
                    
                    if 'Production' in title:
                        resource_name = self._map_tracker_to_resource(tracker, title)
                        changes[resource_name] = changes.get(resource_name, 0) + amount
        
        return changes
    
    def _extract_parameter_changes_detailed(self, log_entries: List[Tag]) -> Dict[str, int]:
        """Extract terraforming parameter changes"""
        changes = {}
        
        for entry in log_entries:
            html_content = str(entry)
            
            # Temperature changes
            temp_match = re.search(r'increases.*Temperature.*by \d+ step.*to a value of (-?\d+)', html_content)
            if temp_match:
                changes['temperature'] = int(temp_match.group(1))
            
            # Oxygen changes
            oxygen_match = re.search(r'increases.*Oxygen Level.*by \d+ step.*to a value of (\d+)', html_content)
            if oxygen_match:
                changes['oxygen'] = int(oxygen_match.group(1))
            
            # Ocean changes
            ocean_match = re.search(r'increases.*Oceans.*by \d+ step.*to a value of (\d+)', html_content)
            if ocean_match:
                changes['oceans'] = int(ocean_match.group(1))
        
        return changes
    
    def _extract_parameter_changes_from_description(self, description: str) -> Dict[str, int]:
        """Extract terraforming parameter changes from move description text"""
        changes = {}
        
        # Temperature changes - look for patterns like "Temperature increases by 1 step to a value of -26"
        temp_patterns = [
            r'Temperature.*?increases.*?by \d+ step.*?to a value of (-?\d+)',
            r'increases.*?Temperature.*?by \d+ step.*?to a value of (-?\d+)',
            r'Temperature.*?to a value of (-?\d+)',
            r'Temperature.*?(-?\d+)°C'
        ]
        
        for pattern in temp_patterns:
            temp_match = re.search(pattern, description, re.IGNORECASE)
            if temp_match:
                changes['temperature'] = int(temp_match.group(1))
                logger.debug(f"Found temperature change: {temp_match.group(1)}")
                break
        
        # Oxygen changes - look for patterns like "Oxygen Level increases by 1 step to a value of 5"
        oxygen_patterns = [
            r'Oxygen Level.*?increases.*?by \d+ step.*?to a value of (\d+)',
            r'increases.*?Oxygen Level.*?by \d+ step.*?to a value of (\d+)',
            r'Oxygen Level.*?to a value of (\d+)',
            r'Oxygen.*?(\d+)%'
        ]
        
        for pattern in oxygen_patterns:
            oxygen_match = re.search(pattern, description, re.IGNORECASE)
            if oxygen_match:
                changes['oxygen'] = int(oxygen_match.group(1))
                logger.debug(f"Found oxygen change: {oxygen_match.group(1)}")
                break
        
        # Ocean changes - look for patterns like "Oceans increases by 1 step to a value of 3"
        ocean_patterns = [
            r'Oceans.*?increases.*?by \d+ step.*?to a value of (\d+)',
            r'increases.*?Oceans.*?by \d+ step.*?to a value of (\d+)',
            r'Oceans.*?to a value of (\d+)',
            r'Ocean.*?(\d+)'
        ]
        
        for pattern in ocean_patterns:
            ocean_match = re.search(pattern, description, re.IGNORECASE)
            if ocean_match:
                changes['oceans'] = int(ocean_match.group(1))
                logger.debug(f"Found ocean change: {ocean_match.group(1)}")
                break
        
        return changes
    
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
    
    def _map_tracker_to_resource(self, tracker: str, title: str) -> str:
        """Map tracker code to resource name"""
        mapping = {
            'm': 'M€',
            's': 'Steel',
            'u': 'Titanium',
            'p': 'Plant',
            'e': 'Energy',
            'h': 'Heat',
            'tr': 'TR',
            'pm': 'M€',
            'ps': 'Steel',
            'pu': 'Titanium',
            'pp': 'Plant',
            'pe': 'Energy',
            'ph': 'Heat',
        }
        
        return mapping.get(tracker, title.replace(' Production', ''))
    
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
    
    def _validate_resource_value(self, resource: str, value: int, is_production: bool = False) -> int:
        """Validate and clamp resource values to valid ranges"""
        if is_production:
            # Production minimums in Terraforming Mars
            minimums = {
                'M€': -5,  # Can go negative due to certain cards
                'Steel': 0,
                'Titanium': 0,
                'Plant': 0,
                'Energy': 0,
                'Heat': 0
            }
            min_val = minimums.get(resource, 0)
            return max(min_val, value)
        else:
            # Regular resources can't go below 0 (except M€ which can be negative)
            if resource == 'M€':
                return value  # M€ can be negative
            elif resource == 'TR':
                return max(20, min(63, value))  # TR range is 20-63
            else:
                return max(0, value)  # Other resources can't be negative

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
    
    def _parse_milestone_award_data(self, gamelogs: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse milestone and award data from g_gamelogs"""
        milestones_data = {}
        awards_data = {}
        
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
                    
                    # Look for milestone claims
                    log_message = data_item.get('log', '')
                    if 'milestone' in log_message.lower():
                        args = data_item.get('args', {})
                        if 'player_name' in args:
                            milestone_info = {
                                'move_id': entry.get('move_id'),
                                'time': entry.get('time'),
                                'player_id': args.get('player_id'),
                                'player_name': args.get('player_name'),
                                'uid': data_item.get('uid')
                            }
                            milestone_key = f"milestone_{data_item.get('uid', 'unknown')}"
                            milestones_data[milestone_key] = milestone_info
                    
                    # Look for award funding
                    if 'award' in log_message.lower() and 'fund' in log_message.lower():
                        args = data_item.get('args', {})
                        if 'player_name' in args:
                            award_info = {
                                'move_id': entry.get('move_id'),
                                'time': entry.get('time'),
                                'player_id': args.get('player_id'),
                                'player_name': args.get('player_name'),
                                'uid': data_item.get('uid')
                            }
                            award_key = f"award_{data_item.get('uid', 'unknown')}"
                            awards_data[award_key] = award_info
            
            logger.info(f"Extracted {len(milestones_data)} milestone entries and {len(awards_data)} award entries")
            return milestones_data, awards_data
            
        except Exception as e:
            logger.error(f"Error parsing milestone/award data: {e}")
            return {}, {}
    
    def _extract_vp_progression(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract VP progression throughout the game using g_gamelogs data"""
        # Extract g_gamelogs first
        gamelogs = self._extract_g_gamelogs(html_content)
        if not gamelogs:
            # Fallback to old method if g_gamelogs not found
            return self._extract_vp_progression_fallback(html_content)
        
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
    
    def _extract_parameter_progression(self, moves: List[Move]) -> List[Dict[str, Any]]:
        """Extract parameter progression from moves"""
        progression = []
        
        for move in moves:
            if move.game_state:
                progression.append({
                    'move_number': move.game_state.move_number,
                    'generation': move.game_state.generation,
                    'temperature': move.game_state.temperature,
                    'oxygen': move.game_state.oxygen,
                    'oceans': move.game_state.oceans
                })
        
        return progression
    
    def _extract_vp_data_from_html(self, html_content: str) -> Dict[str, Any]:
        """Extract VP data from HTML - reusing existing logic"""
        pattern = r'"data":\{("(\d+)":\{.*?"total":(\d+).*?\}.*?"(\d+)":\{.*?"total":(\d+).*?\})\}'
        
        matches = re.findall(pattern, html_content, re.DOTALL)
        
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
                    
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        return {}
    
    def _extract_player_id_mapping(self, html_content: str, player_names: List[str]) -> Dict[str, str]:
        """Extract player ID mapping with optimized regex to prevent catastrophic backtracking"""
        player_id_map = {}
        
        try:
            # Get valid player IDs from VP data
            vp_data = self._extract_vp_data_from_html(html_content)
            valid_player_ids = set(vp_data.keys())
            
            logger.info(f"Found {len(valid_player_ids)} valid player IDs: {valid_player_ids}")
            
            # First, try to get mapping from gamelogs (most reliable)
            gamelogs = self._extract_g_gamelogs(html_content)
            if gamelogs:
                logger.info("Attempting to extract player mapping from gamelogs")
                gamelogs_mapping = self._extract_player_mapping_from_gamelogs(gamelogs, valid_player_ids)
                if gamelogs_mapping:
                    logger.info(f"Found gamelogs mapping: {gamelogs_mapping}")
                    # Update player_names to use the correct names from gamelogs
                    gamelogs_names = list(gamelogs_mapping.keys())
                    player_id_map.update(gamelogs_mapping)
                    
                    # If we got a complete mapping from gamelogs, return it
                    if len(player_id_map) == len(valid_player_ids):
                        logger.info(f"Complete mapping from gamelogs: {player_id_map}")
                        return player_id_map
            
            # If gamelogs didn't provide complete mapping, fall back to HTML-based search
            # Use the original player_names passed in, but also try gamelogs names if available
            names_to_try = list(player_names)
            if 'gamelogs_names' in locals():
                # Add gamelogs names that aren't already mapped
                for name in gamelogs_names:
                    if name not in player_id_map and name not in names_to_try:
                        names_to_try.append(name)
            
            logger.info(f"Trying HTML-based mapping for names: {names_to_try}")
            
            # Look for player board elements that might contain the mapping
            for player in names_to_try:
                if player in player_id_map:
                    continue
                    
                logger.debug(f"Searching for player ID mapping for: {player}")
                
                # Use more specific and efficient patterns to avoid catastrophic backtracking
                patterns = [
                    # Look for player name followed by digits within reasonable distance (max 100 chars)
                    rf'{re.escape(player)}.{{0,100}}?(\d{{8,}})',
                    # Look for digits followed by player name within reasonable distance
                    rf'(\d{{8,}}).{{0,100}}?{re.escape(player)}',
                    # Look in player board contexts
                    rf'player_board.{{0,200}}?{re.escape(player)}.{{0,100}}?(\d{{8,}})',
                    rf'(\d{{8,}}).{{0,100}}?player_board.{{0,200}}?{re.escape(player)}',
                ]
                
                for i, pattern in enumerate(patterns):
                    try:
                        # Use a more targeted search by looking in smaller chunks
                        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                        logger.debug(f"Pattern {i+1} for {player}: found {len(matches)} matches")
                        
                        if matches:
                            for match in matches:
                                match_id = match if isinstance(match, str) else match[0] if isinstance(match, tuple) else str(match)
                                if len(match_id) >= 8 and match_id in valid_player_ids:
                                    player_id_map[player] = match_id
                                    logger.info(f"Mapped {player} -> {match_id}")
                                    break
                            
                            if player in player_id_map:
                                break
                                
                    except re.error as e:
                        logger.warning(f"Regex error for pattern {i+1} with player {player}: {e}")
                        continue
                
                # If still not found, try a simpler approach
                if player not in player_id_map:
                    # Look for the player name in a smaller context around player boards
                    try:
                        player_sections = re.findall(rf'player_board[^>]*>.{{0,500}}?{re.escape(player)}.{{0,500}}?</div>', 
                                                    html_content, re.IGNORECASE | re.DOTALL)
                        
                        for section in player_sections:
                            digit_matches = re.findall(r'\d{8,}', section)
                            for digit_match in digit_matches:
                                if digit_match in valid_player_ids:
                                    player_id_map[player] = digit_match
                                    logger.info(f"Mapped {player} -> {digit_match} (fallback method)")
                                    break
                            if player in player_id_map:
                                break
                    except re.error as e:
                        logger.warning(f"Regex error in fallback method for player {player}: {e}")
            
            # Final fallback mapping if HTML-based mapping fails
            if len(player_id_map) < len(valid_player_ids):
                logger.warning(f"Only mapped {len(player_id_map)}/{len(valid_player_ids)} players, using fallback")
                player_ids = sorted(valid_player_ids)
                mapped_ids = set(player_id_map.values())
                
                # Map any remaining unmapped IDs to remaining names
                unmapped_ids = [pid for pid in player_ids if pid not in mapped_ids]
                unmapped_names = [name for name in names_to_try if name not in player_id_map]
                
                for i, player in enumerate(unmapped_names):
                    if i < len(unmapped_ids):
                        player_id_map[player] = unmapped_ids[i]
                        logger.info(f"Fallback mapping: {player} -> {unmapped_ids[i]}")
            
            logger.info(f"Final player ID mapping: {player_id_map}")
            return player_id_map
            
        except Exception as e:
            logger.error(f"Error in player ID mapping extraction: {e}")
            
            # Return simple fallback mapping
            fallback_map = {}
            for i, player in enumerate(player_names):
                fallback_map[player] = f"unknown_{i}"
            
            return fallback_map
    
    def _extract_player_mapping_from_gamelogs(self, gamelogs: Dict[str, Any], valid_player_ids: set) -> Dict[str, str]:
        """Extract player name to ID mapping from gamelogs data"""
        mapping = {}
        
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
                    
                    args = data_item.get('args', {})
                    
                    # Look for entries that have both player_id and player_name
                    if 'player_id' in args and 'player_name' in args:
                        player_id = str(args['player_id'])
                        player_name = args['player_name']
                        
                        # Only use if it's a valid player ID
                        if player_id in valid_player_ids:
                            mapping[player_name] = player_id
                            logger.debug(f"Gamelogs mapping: {player_name} -> {player_id}")
            
            logger.info(f"Extracted {len(mapping)} player mappings from gamelogs")
            return mapping
            
        except Exception as e:
            logger.error(f"Error extracting player mapping from gamelogs: {e}")
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
    
    def _determine_winner(self, players_info: Dict[str, Player]) -> str:
        """Determine the winner based on final VP"""
        if not players_info:
            return "Unknown"
        
        max_vp = max(player.final_vp for player in players_info.values())
        winners = [player.player_name for player in players_info.values() if player.final_vp == max_vp]
        
        return winners[0] if winners else "Unknown"
    
    def _extract_game_date(self, soup: BeautifulSoup) -> str:
        """Extract game date from HTML"""
        # Look for date information in the HTML
        # This would need to be customized based on BGA's HTML structure
        return datetime.now().strftime("%Y-%m-%d")
    
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
            'total_moves': total_moves,
            'html_length': len(html_content)
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

    def _infer_tracker_display_name(self, tracker_id: str, html_content: str) -> str:
        """Infer display name for a tracker from HTML context"""
        try:
            # Find the section of HTML around this tracker ID
            tracker_pattern = rf'id="{re.escape(tracker_id)}"'
            match = re.search(tracker_pattern, html_content)
            
            if not match:
                return ""
            
            # Extract surrounding context (500 chars before and after)
            start = max(0, match.start() - 500)
            end = min(len(html_content), match.end() + 500)
            context = html_content[start:end]
            
            # Look for common patterns that indicate the tracker type
            if "counter_hand" in tracker_id:
                return "Hand Counter"
            elif "tracker_m_" in tracker_id and "production" not in context.lower():
                return "MC"
            elif "tracker_pm_" in tracker_id or ("tracker_m_" in tracker_id and "production" in context.lower()):
                return "MC Production"
            elif "tracker_s_" in tracker_id and "production" not in context.lower():
                return "Steel"
            elif "tracker_ps_" in tracker_id or ("tracker_s_" in tracker_id and "production" in context.lower()):
                return "Steel Production"
            elif "tracker_u_" in tracker_id and "production" not in context.lower():
                return "Titanium"
            elif "tracker_pu_" in tracker_id or ("tracker_u_" in tracker_id and "production" in context.lower()):
                return "Titanium Production"
            elif "tracker_p_" in tracker_id and "production" not in context.lower():
                return "Plant"
            elif "tracker_pp_" in tracker_id or ("tracker_p_" in tracker_id and "production" in context.lower()):
                return "Plant Production"
            elif "tracker_e_" in tracker_id and "production" not in context.lower():
                return "Energy"
            elif "tracker_pe_" in tracker_id or ("tracker_e_" in tracker_id and "production" in context.lower()):
                return "Energy Production"
            elif "tracker_h" in tracker_id and "production" not in context.lower():
                return "Heat"
            elif "tracker_ph_" in tracker_id or ("tracker_h" in tracker_id and "production" in context.lower()):
                return "Heat Production"
            elif "tracker_tagBuilding" in tracker_id:
                return "Count of Building tags"
            elif "tracker_tagSpace" in tracker_id:
                return "Count of Space tags"
            elif "tracker_tagScience" in tracker_id:
                return "Count of Science tags"
            elif "tracker_tagEnergy" in tracker_id:
                return "Count of Power tags"
            elif "tracker_tagEarth" in tracker_id:
                return "Count of Earth tags"
            elif "tracker_tagJovian" in tracker_id:
                return "Count of Jovian tags"
            elif "tracker_tagCity" in tracker_id:
                return "Count of City tags"
            elif "tracker_tagPlant" in tracker_id:
                return "Count of Plant tags"
            elif "tracker_tagMicrobe" in tracker_id:
                return "Count of Microbe tags"
            elif "tracker_tagAnimal" in tracker_id:
                return "Count of Animal tags"
            elif "tracker_tagWild" in tracker_id:
                return "Count of Wild tags"
            elif "tracker_tagEvent" in tracker_id:
                return "Count of played Events cards"
            
            return ""
            
        except Exception as e:
            logger.error(f"Error inferring display name for {tracker_id}: {e}")
            return ""

    def _extract_player_color_codes(self, html_content: str) -> List[str]:
        """Extract player color codes from HTML elements"""
        color_codes = set()
        
        try:
            # Pattern 1: Extract from player_panel_content_XXXXXX
            panel_pattern = r'id="player_panel_content_([a-f0-9]{6})"'
            panel_matches = re.findall(panel_pattern, html_content, re.IGNORECASE)
            color_codes.update(panel_matches)
            
            # Pattern 2: Extract from miniboard_XXXXXX
            miniboard_pattern = r'id="miniboard_([a-f0-9]{6})"'
            miniboard_matches = re.findall(miniboard_pattern, html_content, re.IGNORECASE)
            color_codes.update(miniboard_matches)
            
            # Pattern 3: Extract from tracker IDs directly
            tracker_pattern = r'id="(?:counter_hand|tracker_[a-z]+)_([a-f0-9]{6})"'
            tracker_matches = re.findall(tracker_pattern, html_content, re.IGNORECASE)
            color_codes.update(tracker_matches)
            
            # Pattern 4: Extract from player_board_inner_XXXXXX
            board_inner_pattern = r'id="player_board_inner_([a-f0-9]{6})"'
            board_inner_matches = re.findall(board_inner_pattern, html_content, re.IGNORECASE)
            color_codes.update(board_inner_matches)
            
            result = sorted(list(color_codes))
            logger.info(f"Extracted {len(result)} player color codes: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting player color codes: {e}")
            return []

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

    def _create_player_color_mapping(self, player_ids: List[str], tracker_dict: Dict[str, str]) -> Dict[str, str]:
        """Create mapping from player color codes to actual player IDs"""
        color_to_id = {}
        
        # Extract color codes from tracker dictionary keys
        color_codes = set()
        for tracker_id in tracker_dict.keys():
            # Extract color code from tracker IDs like "counter_hand_ff0000"
            parts = tracker_id.split('_')
            if len(parts) >= 3 and len(parts[-1]) == 6:
                color_codes.add(parts[-1])
        
        # Map color codes to player IDs (simple mapping by order)
        color_list = sorted(list(color_codes))
        player_list = sorted(player_ids)
        
        for i, color in enumerate(color_list):
            if i < len(player_list):
                color_to_id[color] = player_list[i]
        
        return color_to_id

    def _categorize_tracker_data(self, tracker_name: str, value) -> Tuple[str, str, int]:
        """Categorize tracker data into resources, production, tags, etc."""
        # Convert value to int if it's a string
        try:
            validated_value = int(value)
        except (ValueError, TypeError):
            validated_value = 0
        
        if "Production" in tracker_name:
            # Production values - validate with minimums
            if "MC" in tracker_name:
                validated_value = max(-5, validated_value)  # MC production can go to -5
            else:
                validated_value = max(0, validated_value)  # Other production can't go below 0
            category = "production"
            clean_name = tracker_name.replace(" Production", "")
        elif "Count of" in tracker_name or "tags" in tracker_name.lower():
            # Tag counts - can't be negative
            validated_value = max(0, validated_value)
            category = "tags"
            clean_name = tracker_name.replace("Count of ", "").replace(" tags", "")
        elif "Hand Counter" in tracker_name:
            # Hand count - can't be negative
            validated_value = max(0, validated_value)
            category = "hand_count"
            clean_name = "Hand"
        else:
            # Regular resources
            if tracker_name == "MC":
                validated_value = validated_value  # MC can be negative
            else:
                validated_value = max(0, validated_value)  # Other resources can't be negative
            category = "resources"
            clean_name = tracker_name
        
        return category, clean_name, validated_value

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
        """Parse a complete game with ELO data from both replay and table HTML"""
        logger.info(f"Starting parsing with ELO data for game {table_id}")
        
        # Parse ELO data from table HTML first to get player names
        elo_data = self.parse_elo_data(table_html)
        logger.info(f"Found ELO data for players: {list(elo_data.keys())}")
        
        # Parse the main game data from replay HTML
        game_data = self.parse_complete_game(replay_html, table_id, player_perspective)
        
        # Validate that we have meaningful game data before proceeding
        has_meaningful_data = self._validate_meaningful_game_data(game_data, replay_html)
        
        # If no players were found in replay HTML, create them from ELO data
        if not game_data.players and elo_data:
            logger.info("No players found in replay HTML, creating from ELO data")
            game_data.players = self._create_players_from_elo_data(elo_data, replay_html, table_id)
        
        # Merge ELO data into player information
        self._merge_elo_with_players(game_data.players, elo_data)
        
        # Update metadata to indicate ELO data was included
        game_data.metadata['elo_data_included'] = len(elo_data) > 0
        game_data.metadata['elo_players_found'] = len(elo_data)
        game_data.metadata['has_meaningful_data'] = has_meaningful_data
        game_data.metadata['elo_only_fallback'] = not has_meaningful_data and len(elo_data) > 0
        
        # If we only have ELO data and no meaningful game data, this should be considered a parsing failure
        if not has_meaningful_data:
            logger.warning(f"Game {table_id} only has ELO data, no meaningful replay data found")
            logger.warning("This indicates the replay HTML is missing or corrupted")
            raise ValueError(f"No meaningful game data found for {table_id} - only ELO data available. This suggests replay HTML is missing or incomplete.")
        
        logger.info(f"Parsing with ELO complete for game {table_id}: ELO data found for {len(elo_data)} players")
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
                    player_name = player_elo.pop('player_name')
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
            
            if len(newranks) >= 2:
                game_newrank_text = newranks[1].get_text().strip()
                # Extract game rank (current)
                game_rank_match = re.search(r'(\d+)', game_newrank_text)
                if game_rank_match:
                    player_data['game_rank'] = int(game_rank_match.group(1))
            
            logger.info(f"Extracted ELO data for {player_name}: {player_data}")
            return player_data if len(player_data) > 1 else None  # Must have more than just player_name
            
        except Exception as e:
            logger.error(f"Error parsing player from score entry: {e}")
            return None

    def _parse_single_player_elo(self, rank_section: Tag, html_content: str) -> Optional[Dict[str, Any]]:
        """Parse ELO data for a single player from their rank section"""
        try:
            player_data = {}
            
            # Extract player name
            player_name_elem = rank_section.find('span', class_='playername')
            if not player_name_elem:
                return None
            
            player_data['player_name'] = player_name_elem.get_text().strip()
            
            # Extract Arena points (current season points)
            arena_points_elem = rank_section.find('div', id=lambda x: x and 'winpoints' in x)
            if arena_points_elem:
                # Look for the points value - typically a number like "1754"
                points_text = arena_points_elem.get_text()
                arena_points_match = re.search(r'(\d+)\s*pts', points_text)
                if arena_points_match:
                    player_data['arena_points'] = int(arena_points_match.group(1))
                else:
                    # Try to find just a number
                    number_match = re.search(r'(\d+)', points_text)
                    if number_match:
                        player_data['arena_points'] = int(number_match.group(1))
            
            # Extract Arena points change (gain/loss from this game)
            # Look for patterns like "+24" or "-5"
            change_pattern = r'([+-]\d+)'
            change_matches = re.findall(change_pattern, str(rank_section))
            if change_matches:
                # Take the first change value found
                player_data['arena_points_change'] = int(change_matches[0])
            
            # Extract Game rank (actual ELO rating)
            # Look for gamerank elements or patterns
            gamerank_elem = rank_section.find('div', class_='gamerank')
            if gamerank_elem:
                rank_text = gamerank_elem.get_text()
                rank_match = re.search(r'(\d+)', rank_text)
                if rank_match:
                    player_data['game_rank'] = int(rank_match.group(1))
            else:
                # Alternative: look for rank patterns in the HTML
                rank_pattern = r'gamerank[^>]*>.*?(\d+)'
                rank_match = re.search(rank_pattern, str(rank_section))
                if rank_match:
                    player_data['game_rank'] = int(rank_match.group(1))
            
            # Extract Game rank change
            # This might be in a separate element or combined with the rank
            rank_change_pattern = r'gamerank[^>]*>.*?([+-]\d+)'
            rank_change_match = re.search(rank_change_pattern, str(rank_section))
            if rank_change_match:
                player_data['game_rank_change'] = int(rank_change_match.group(1))
            
            return player_data if len(player_data) > 1 else None  # Must have more than just player_name
            
        except Exception as e:
            logger.error(f"Error parsing single player ELO: {e}")
            return None

    def _find_associated_player_name(self, element: Tag, soup: BeautifulSoup) -> Optional[str]:
        """Find the player name associated with an ELO element"""
        # Look for player name in parent elements
        current = element
        for _ in range(5):  # Search up to 5 levels up
            if current.parent:
                current = current.parent
                player_elem = current.find('span', class_='playername')
                if player_elem:
                    return player_elem.get_text().strip()
        
        # Look for player name in sibling elements
        siblings = element.find_next_siblings() + element.find_previous_siblings()
        for sibling in siblings:
            if hasattr(sibling, 'find'):
                player_elem = sibling.find('span', class_='playername')
                if player_elem:
                    return player_elem.get_text().strip()
        
        return None
    
    def _create_players_from_elo_data(self, elo_data: Dict[str, EloData], replay_html: str, table_id: str) -> Dict[str, Player]:
        """Create player objects from ELO data when replay HTML doesn't contain player info"""
        logger.info(f"Creating players from ELO data for {len(elo_data)} players")
        
        players = {}
        soup = BeautifulSoup(replay_html, 'html.parser')
        
        # Get VP data for final scores
        vp_data = self._extract_vp_data_from_html(replay_html)
        
        # Get corporations from replay HTML
        corporations = self._extract_corporations(soup)
        
        for i, (player_name, elo_info) in enumerate(elo_data.items()):
            # Create a player ID - try to find from VP data or use fallback
            player_id = None
            
            # Try to find player ID from VP data
            for vp_player_id, vp_player_data in vp_data.items():
                # This is a simple heuristic - could be improved
                if len(vp_data) == len(elo_data):
                    # If we have the same number of players in both, map by order
                    player_ids = sorted(vp_data.keys())
                    if i < len(player_ids):
                        player_id = player_ids[i]
                        break
            
            if not player_id:
                player_id = f"player_{i}"
            
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

    def _validate_meaningful_game_data(self, game_data: GameData, replay_html: str) -> bool:
        """
        Validate that we have meaningful game data, not just ELO fallback data
        
        Args:
            game_data: Parsed game data
            replay_html: Original replay HTML content
            
        Returns:
            bool: True if we have meaningful game data, False if only ELO fallback
        """
        try:
            # Check for meaningful indicators of actual game data
            meaningful_indicators = 0
            
            # 1. Check if we have actual moves (not just 0)
            if len(game_data.moves) > 0:
                meaningful_indicators += 1
                logger.debug(f"Found {len(game_data.moves)} moves")
            
            # 2. Check if we have corporation data
            corporations_found = 0
            for player in game_data.players.values():
                if player.corporation and player.corporation != 'Unknown':
                    corporations_found += 1
            
            if corporations_found > 0:
                meaningful_indicators += 1
                logger.debug(f"Found {corporations_found} corporations")
            
            # 3. Check if we have card mappings in the HTML (indicates replay data)
            card_names = self._extract_card_names(replay_html)
            if len(card_names) > 0:
                meaningful_indicators += 1
                logger.debug(f"Found {len(card_names)} card mappings")
            
            # 4. Check if we have milestone/award mappings
            milestone_names = self._extract_milestone_names(replay_html)
            award_names = self._extract_award_names(replay_html)
            if len(milestone_names) > 0 or len(award_names) > 0:
                meaningful_indicators += 1
                logger.debug(f"Found {len(milestone_names)} milestones, {len(award_names)} awards")
            
            # 5. Check if we have gamelogs data (strong indicator of replay HTML)
            gamelogs = self._extract_g_gamelogs(replay_html)
            if gamelogs and 'data' in gamelogs:
                meaningful_indicators += 1
                logger.debug("Found gamelogs data")
            
            # 6. Check if we have VP progression data
            vp_progression = self._extract_vp_progression(replay_html)
            if len(vp_progression) > 1:  # More than just initial state
                meaningful_indicators += 1
                logger.debug(f"Found {len(vp_progression)} VP progression entries")
            
            # 7. Check if we have actual game generations > 1
            if game_data.generations > 1:
                meaningful_indicators += 1
                logger.debug(f"Found {game_data.generations} generations")
            
            # We need at least 3 meaningful indicators AND must have moves OR corporations
            # This prevents cases where we have some replay data but no actual gameplay
            has_core_gameplay = len(game_data.moves) > 0 or corporations_found > 0
            is_meaningful = meaningful_indicators >= 3 and has_core_gameplay
            
            logger.info(f"Validation result: {meaningful_indicators}/7 indicators found, meaningful={is_meaningful}")
            
            if not is_meaningful:
                logger.warning("Game data validation failed - appears to be ELO-only fallback data")
                logger.warning(f"Indicators found: moves={len(game_data.moves)}, corporations={corporations_found}, "
                             f"cards={len(card_names)}, milestones/awards={len(milestone_names)+len(award_names)}, "
                             f"gamelogs={'yes' if gamelogs else 'no'}, vp_entries={len(vp_progression)}, "
                             f"generations={game_data.generations}")
            
            return is_meaningful
            
        except Exception as e:
            logger.error(f"Error validating game data: {e}")
            return False

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
