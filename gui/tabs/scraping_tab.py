"""
Unified Scraping Tab for BGA TM Scraper GUI
Handles both getting assignments and running scraping operations
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
import requests
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ScrapingTab:
    """Unified scraping tab for assignments and scraping operations"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Assignment state
        self.current_assignment = None
        
        # Scraping state
        self.is_scraping = False
        self.scraping_thread = None
        self.should_stop = False
        
        # Progress tracking
        self.total_items = 0
        self.completed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.start_time = None
        
        # Progress persistence
        self.current_assignment_id = None
        self.existing_progress = None
        
        # Create the UI
        self.create_widgets()
        
        # Load saved game count
        self._load_game_count()
        
        # Check for existing assignment
        self.check_assignment()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Scraping", 
                               font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Assignment status frame
        self.assignment_status_frame = ttk.LabelFrame(main_frame, text="Assignment Status", padding=15)
        self.assignment_status_frame.pack(fill="x", pady=(0, 20))
        
        # No assignment message (initially shown)
        self.no_assignment_label = ttk.Label(
            self.assignment_status_frame,
            text="No assignment loaded. Click 'Get Next Assignment' to receive your task.",
            foreground="gray",
            font=("TkDefaultFont", 10, "italic")
        )
        self.no_assignment_label.pack(expand=True)
        
        # Assignment details frame (initially hidden)
        self.assignment_details_frame = ttk.Frame(self.assignment_status_frame)
        
        # Assignment type and description
        self.assignment_type_label = ttk.Label(
            self.assignment_details_frame, 
            text="", 
            font=("TkDefaultFont", 12, "bold")
        )
        self.assignment_type_label.pack(anchor="w", pady=(0, 5))
        
        self.assignment_desc_label = ttk.Label(
            self.assignment_details_frame, 
            text="", 
            justify="left"
        )
        self.assignment_desc_label.pack(anchor="w", pady=(0, 10))
        
        # Assignment summary info
        self.assignment_summary_frame = ttk.Frame(self.assignment_details_frame)
        self.assignment_summary_frame.pack(fill="x", pady=(0, 10))
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=(0, 20))
        
        # Game count input frame
        game_count_frame = ttk.Frame(control_frame)
        game_count_frame.pack(side="left", padx=(0, 10))
        
        ttk.Label(game_count_frame, text="Games (max 200):").pack(side="left")
        self.game_count_var = tk.StringVar()
        self.game_count_spinbox = ttk.Spinbox(
            game_count_frame,
            from_=1,
            to=200,
            textvariable=self.game_count_var,
            width=8,
            validate="key",
            validatecommand=(self.frame.register(self._validate_game_count), "%P")
        )
        self.game_count_spinbox.pack(side="left", padx=(5, 0))
        
        # Error label for validation (initially hidden)
        self.game_count_error_label = ttk.Label(
            main_frame,
            text="",
            foreground="red",
            font=("TkDefaultFont", 9)
        )
        
        # Get assignment button
        self.get_assignment_btn = ttk.Button(
            control_frame,
            text="🎯 Get Next Assignment",
            command=self.get_assignment
        )
        self.get_assignment_btn.pack(side="left", padx=(10, 10))
        
        # Start button
        self.start_btn = ttk.Button(
            control_frame,
            text="🚀 Start Scraping",
            command=self.start_scraping,
            style="Accent.TButton",
            state="disabled"
        )
        self.start_btn.pack(side="left", padx=(0, 10))
        
        # Stop button
        self.stop_btn = ttk.Button(
            control_frame,
            text="⏹️ Stop Scraping",
            command=self.stop_scraping,
            state="disabled"
        )
        self.stop_btn.pack(side="left")
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding=15)
        progress_frame.pack(fill="both", expand=True)
        
        # Overall progress
        progress_info_frame = ttk.Frame(progress_frame)
        progress_info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(progress_info_frame, text="Overall Progress:").pack(side="left")
        self.progress_label = ttk.Label(progress_info_frame, text="0 / 0 (0%)", font=("TkDefaultFont", 10, "bold"))
        self.progress_label.pack(side="right")
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 15))
        
        # Current operation
        current_op_frame = ttk.Frame(progress_frame)
        current_op_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(current_op_frame, text="Current Operation:").pack(side="left")
        self.current_op_label = ttk.Label(current_op_frame, text="Idle", foreground="gray")
        self.current_op_label.pack(side="right")
        
        # Statistics frame
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill="x", pady=(0, 10))
        
        # Success/failure counters
        self.success_label = ttk.Label(stats_frame, text="✅ Success: 0", foreground="green")
        self.success_label.pack(side="left")
        
        self.failure_label = ttk.Label(stats_frame, text="❌ Failed: 0", foreground="red")
        self.failure_label.pack(side="left", padx=(20, 0))
        
        # Time info
        self.time_label = ttk.Label(stats_frame, text="⏱️ Elapsed: 00:00:00")
        self.time_label.pack(side="right")
        
        # Log display
        log_frame = ttk.LabelFrame(progress_frame, text="Activity Log", padding=5)
        log_frame.pack(fill="both", expand=True, pady=(15, 0))
        
        # Create text widget with scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(
            log_container,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#f8f8f8"
        )
        
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Clear log button
        clear_log_btn = ttk.Button(log_frame, text="Clear Log", command=self.clear_log)
        clear_log_btn.pack(pady=(5, 0))
    
    def get_assignment(self):
        """Get a new assignment from the API"""
        # Check if there's an incomplete assignment
        current_status = self.config_manager.get_value("current_assignment", "status")
        
        if current_status in ["ready", "in_progress"]:
            # Show warning dialog
            result = messagebox.askyesno(
                "Abandon Current Assignment?",
                "You have an incomplete assignment. Getting a new one will abandon "
                "the current assignment and may lock up games for other users.\n\n"
                "Are you sure you want to continue?",
                icon="warning"
            )
            if not result:
                return  # User cancelled
        
        # Disable button during request
        self.get_assignment_btn.config(state="disabled", text="Getting assignment...")
        self.frame.update()
        
        # Start API request in background thread
        api_thread = threading.Thread(target=self._fetch_assignment_from_api, daemon=True)
        api_thread.start()
    
    def _fetch_assignment_from_api(self):
        """Fetch assignment from the real API"""
        try:
            # Validate configuration
            api_key = self.config_manager.get_value("api_settings", "api_key")
            bga_email = self.config_manager.get_value("bga_credentials", "email")
            
            if not api_key:
                self.frame.after(0, lambda: self._show_config_error("API key is not configured. Please set it in Settings."))
                return
            
            if not bga_email:
                self.frame.after(0, lambda: self._show_config_error("BGA email is not configured. Please set it in Settings."))
                return
            
            # Validate and get game count
            game_count = self._get_validated_game_count()
            if game_count is False:  # Invalid input
                self.frame.after(0, lambda: self.get_assignment_btn.config(state="normal", text="� Get Next Assignment"))
                return
            
            # Save game count to config if valid
            if game_count is not None:
                self._save_game_count()
                self.frame.after(0, lambda: self.log_message(f"🌐 Requesting assignment from API (requesting {game_count} games)..."))
            else:
                self.frame.after(0, lambda: self.log_message(f"🌐 Requesting assignment from API..."))
            
            # Create API client and make request
            api_client = self._create_api_client(api_key)
            assignment_data = api_client.get_next_assignment(bga_email, game_count)
            
            if assignment_data:
                self.frame.after(0, lambda: self._process_api_assignment(assignment_data))
            else:
                self.frame.after(0, lambda: self._show_no_assignments())
                
        except requests.exceptions.Timeout:
            self.frame.after(0, lambda: self._show_api_error("Request timed out. Please check your internet connection."))
        except requests.exceptions.ConnectionError:
            self.frame.after(0, lambda: self._show_api_error("Could not connect to the API. Please check your internet connection."))
        except Exception as e:
            self.frame.after(0, lambda: self._show_api_error(f"Unexpected error: {str(e)}"))
    
    def _process_api_assignment(self, assignment_data):
        """Process assignment data from the API"""
        try:
            # Parse assignment based on type
            assignment_type = assignment_data.get("assignmentType", "").lower()
            
            if assignment_type == "indexing":
                self.current_assignment = self._parse_indexing_assignment(assignment_data)
            elif assignment_type == "replayscraping":
                self.current_assignment = self._parse_replay_assignment(assignment_data)
            else:
                raise ValueError(f"Unknown assignment type: {assignment_type}")
            
            # Generate assignment ID and check for existing progress
            self.current_assignment_id = self.config_manager.generate_assignment_id(self.current_assignment)
            self.existing_progress = self.config_manager.load_assignment_progress(self.current_assignment_id)
            
            # Show assignment
            self._display_assignment()
            
            # Update start button text based on existing progress
            self._update_start_button_text()
            
            # Enable start button
            self.start_btn.config(state="normal")
            
            # Re-enable get assignment button
            self.get_assignment_btn.config(state="normal", text="🎯 Get Next Assignment")
            
            # Store assignment in config
            self.config_manager.set_value("current_assignment", "data", self.current_assignment)
            self.config_manager.set_value("current_assignment", "status", "ready")
            self.config_manager.save_config()
            
            if self.existing_progress:
                completed = len(self.existing_progress.get("completed_games", []))
                failed = len(self.existing_progress.get("failed_games", []))
                self.log_message(f"✅ Assignment received - Found existing progress: {completed} completed, {failed} failed")
            else:
                self.log_message("✅ New assignment received and ready to start")
            
        except Exception as e:
            self._show_api_error(f"Failed to process assignment: {str(e)}")
    
    def _parse_indexing_assignment(self, data):
        """Parse an indexing assignment from API data"""
        player_id = data.get("playerId")
        player_name = data.get("playerName", f"Player_{player_id}")
        
        # Estimate games count (we don't know the exact count for indexing)
        estimated_games = random.randint(50, 200)  # Reasonable estimate
        
        return {
            "type": "indexing",
            "title": "🔍 Index Games Assignment",
            "description": f"Index games for {player_name}",
            "details": {
                "player_id": str(player_id),
                "player_name": player_name,
                "estimated_games": estimated_games,
                "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "raw_data": data
        }
    
    def _parse_replay_assignment(self, data):
        """Parse a replay scraping assignment from API data"""
        games = data.get("games", [])
        game_count = len(games)
        
        # Extract player perspective info from first game
        player_perspective_id = None
        player_perspective_name = None
        if games:
            player_perspective_id = games[0].get("playerPerspective")
            player_perspective_name = games[0].get("playerName")
        
        return {
            "type": "replayscraping", 
            "title": "📋 Collect Game Logs Assignment",
            "description": f"Collect logs for {game_count} games",
            "details": {
                "game_count": game_count,
                "player_perspective_id": str(player_perspective_id) if player_perspective_id else "Unknown",
                "player_perspective_name": player_perspective_name or "Unknown",
                "games": games,
                "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "raw_data": data
        }
    
    def _show_config_error(self, message):
        """Show configuration error and re-enable button"""
        messagebox.showerror("Configuration Error", message)
        self.get_assignment_btn.config(state="normal", text="🎯 Get Next Assignment")
        self.log_message(f"❌ Configuration error: {message}")
    
    def _show_api_error(self, message):
        """Show API error and re-enable button"""
        messagebox.showerror("API Error", f"Failed to get assignment:\n{message}")
        self.get_assignment_btn.config(state="normal", text="🎯 Get Next Assignment")
        self.log_message(f"❌ API error: {message}")
    
    def _show_no_assignments(self):
        """Show no assignments available message"""
        messagebox.showinfo("No Assignments", "No assignments are currently available. Please try again later.")
        self.get_assignment_btn.config(state="normal", text="🎯 Get Next Assignment")
        self.log_message("ℹ️ No assignments available")
    
    def _generate_index_assignment(self):
        """Generate a mock index games assignment"""
        # Mock player IDs
        player_ids = [
            "86296239", "12345678", "87654321", "11223344", "99887766"
        ]
        
        selected_player = random.choice(player_ids)
        estimated_games = random.randint(50, 300)
        
        return {
            "type": "index_games",
            "title": "🔍 Index Games Assignment",
            "description": f"Index games for Player {selected_player}",
            "details": {
                "player_id": selected_player,
                "player_name": f"Player_{selected_player}",
                "estimated_games": estimated_games,
                "priority": random.choice(["Normal", "High"]),
                "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    
    def _generate_logs_assignment(self):
        """Generate a mock collect logs assignment"""
        # Mock table IDs with player perspectives
        table_count = 200
        base_table_id = random.randint(600000000, 700000000)
        player_perspective = random.choice(["86296239", "12345678", "87654321"])
        
        table_ids = []
        for i in range(table_count):
            table_ids.append(f"{base_table_id + i}:{player_perspective}")
        
        return {
            "type": "collect_logs",
            "title": "📋 Collect Game Logs Assignment",
            "description": f"Collect logs for {table_count} games",
            "details": {
                "table_count": table_count,
                "player_perspective": player_perspective,
                "table_ids": table_ids,
                "priority": random.choice(["Normal", "High"]),
                "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    
    def _display_assignment(self):
        """Display the current assignment in the UI"""
        if not self.current_assignment:
            return
        
        # Hide no assignment message
        self.no_assignment_label.pack_forget()
        
        # Show assignment details frame
        self.assignment_details_frame.pack(fill="x", expand=True)
        
        # Update assignment info
        self.assignment_type_label.config(text=self.current_assignment["title"])
        self.assignment_desc_label.config(text=self.current_assignment["description"])
        
        # Clear and update summary frame
        for widget in self.assignment_summary_frame.winfo_children():
            widget.destroy()
        
        details = self.current_assignment["details"]
        assignment_type = self.current_assignment["type"]
        
        if assignment_type == "indexing":
            # Indexing assignment summary
            ttk.Label(self.assignment_summary_frame, text=f"Player ID: {details['player_id']}", 
                     font=("TkDefaultFont", 9)).pack(anchor="w")
            ttk.Label(self.assignment_summary_frame, text=f"Player Name: {details['player_name']}", 
                     font=("TkDefaultFont", 9)).pack(anchor="w")
        elif assignment_type == "replayscraping":
            # Replay scraping assignment summary
            ttk.Label(self.assignment_summary_frame, text=f"Game count: {details['game_count']}", 
                     font=("TkDefaultFont", 9)).pack(anchor="w")
            
            # Show player perspective with name and ID
            player_name = details.get('player_perspective_name', 'Unknown')
            player_id = details.get('player_perspective_id', 'Unknown')
            perspective_text = f"Next player to scrape: {player_name} ({player_id})"
            ttk.Label(self.assignment_summary_frame, text=perspective_text, 
                     font=("TkDefaultFont", 9)).pack(anchor="w")
            
            # Show sample table IDs if available
            if details.get("games") and len(details["games"]) > 0:
                sample_games = details["games"][:3]  # Show first 3 games
                sample_ids = [str(game.get("tableId", "Unknown")) for game in sample_games]
                sample_text = f"Sample table IDs: {', '.join(sample_ids)}"
                if len(details["games"]) > 3:
                    sample_text += "..."
                ttk.Label(self.assignment_summary_frame, text=sample_text, 
                         font=("TkDefaultFont", 9)).pack(anchor="w")
        else:
            # Legacy format support (for mock assignments)
            if assignment_type == "index_games":
                ttk.Label(self.assignment_summary_frame, text=f"Player ID: {details['player_id']}", 
                         font=("TkDefaultFont", 9)).pack(anchor="w")
            elif assignment_type == "collect_logs":
                ttk.Label(self.assignment_summary_frame, text=f"Table Count: {details['table_count']}", 
                         font=("TkDefaultFont", 9)).pack(anchor="w")
                ttk.Label(self.assignment_summary_frame, text=f"Player Perspective: {details['player_perspective']}", 
                         font=("TkDefaultFont", 9)).pack(anchor="w")
        
        # Show priority if available
        if details.get("priority"):
            ttk.Label(self.assignment_summary_frame, text=f"Priority: {details['priority']}", 
                     font=("TkDefaultFont", 9)).pack(anchor="w")
        
        # Always show assigned time
        ttk.Label(self.assignment_summary_frame, text=f"Assigned: {details['assigned_at']}", 
                 font=("TkDefaultFont", 9), foreground="gray").pack(anchor="w")
    
    def check_assignment(self):
        """Check for current assignment and update UI"""
        assignment_data = self.config_manager.get_value("current_assignment", "data")
        assignment_status = self.config_manager.get_value("current_assignment", "status")
        
        if assignment_data and assignment_status in ["ready", "accepted"]:
            self.current_assignment = assignment_data
            # Generate assignment ID and check for existing progress
            self.current_assignment_id = self.config_manager.generate_assignment_id(self.current_assignment)
            self.existing_progress = self.config_manager.load_assignment_progress(self.current_assignment_id)
            
            self._display_assignment()
            self._update_start_button_text()
            self.start_btn.config(state="normal")
            
            if self.existing_progress:
                completed = len(self.existing_progress.get("completed_games", []))
                failed = len(self.existing_progress.get("failed_games", []))
                if completed > 0 or failed > 0:
                    self.log_message(f"📊 Found existing progress: {completed} completed, {failed} failed")
            
        elif assignment_data and assignment_status == "in_progress":
            self.current_assignment = assignment_data
            # Generate assignment ID and check for existing progress
            self.current_assignment_id = self.config_manager.generate_assignment_id(self.current_assignment)
            self.existing_progress = self.config_manager.load_assignment_progress(self.current_assignment_id)
            
            self._display_assignment()
            self._update_start_button_text()
            self.start_btn.config(state="normal")
            self.log_message("⚠️ Assignment was in progress - you can continue or restart")
            
        elif assignment_data and assignment_status == "paused_daily_limit":
            self.current_assignment = assignment_data
            # Generate assignment ID and check for existing progress
            self.current_assignment_id = self.config_manager.generate_assignment_id(self.current_assignment)
            self.existing_progress = self.config_manager.load_assignment_progress(self.current_assignment_id)
            
            self._display_assignment()
            self._update_start_button_text()
            self.start_btn.config(state="normal")
            self.log_message("⚠️ Assignment paused due to daily limit - you can retry when limit resets")
            
        elif assignment_data and assignment_status == "completed":
            self.current_assignment = assignment_data
            self._display_assignment()
            self.start_btn.config(state="disabled")
            self.log_message("✅ Previous assignment completed")
            
        else:
            # No assignment
            self.assignment_details_frame.pack_forget()
            self.no_assignment_label.pack(expand=True)
            self.start_btn.config(state="disabled")
            self.current_assignment = None
        
        # Clean up old progress data (older than 7 days)
        self.config_manager.cleanup_old_progress(days_old=7)
    
    def start_scraping(self):
        """Start the scraping process"""
        if not self.current_assignment:
            messagebox.showwarning("No Assignment", "Please get an assignment first.")
            return
        
        if self.is_scraping:
            return
        
        # Validate configuration
        issues = self.config_manager.validate_config()
        if issues["errors"]:
            error_msg = "Configuration errors found:\n\n"
            for error in issues["errors"]:
                error_msg += f"• {error}\n"
            error_msg += "\nPlease fix these issues in the Settings tab."
            messagebox.showerror("Configuration Error", error_msg)
            return
        
        
        # Initialize scraping
        self.is_scraping = True
        self.should_stop = False
        self.start_time = datetime.now()
        
        # Update UI
        self.get_assignment_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        # Initialize progress based on assignment type
        assignment_type = self.current_assignment["type"]
        if assignment_type == "indexing":
            self.total_items = self.current_assignment["details"]["estimated_games"]
        elif assignment_type == "replayscraping":
            self.total_items = self.current_assignment["details"]["game_count"]
        elif assignment_type == "index_games":  # Legacy mock format
            self.total_items = self.current_assignment["details"]["estimated_games"]
        elif assignment_type == "collect_logs":  # Legacy mock format
            self.total_items = self.current_assignment["details"]["table_count"]
        else:
            self.total_items = 100  # Default fallback
        
        # Generate assignment ID if not already done
        if not self.current_assignment_id:
            self.current_assignment_id = self.config_manager.generate_assignment_id(self.current_assignment)
            self.existing_progress = self.config_manager.load_assignment_progress(self.current_assignment_id)
        
        # Initialize or restore progress
        if self.existing_progress:
            self._restore_progress_from_existing()
        else:
            self.completed_items = 0
            self.successful_items = 0
            self.failed_items = 0
        
        # Initialize progress tracking
        self._initialize_progress_tracking()
        
        self.update_progress()
        
        if self.existing_progress and len(self.existing_progress.get("completed_games", [])) > 0:
            self.log_message("🔄 Resuming scraping operation...")
        else:
            self.log_message("🚀 Starting scraping operation...")
        
        # Start scraping in background thread
        self.scraping_thread = threading.Thread(target=self._scraping_worker, daemon=True)
        self.scraping_thread.start()
        
        # Start progress update timer
        self._update_timer()
    
    def stop_scraping(self):
        """Stop the scraping process"""
        if not self.is_scraping:
            return
        
        if messagebox.askyesno("Stop Scraping", "Are you sure you want to stop scraping?"):
            self.should_stop = True
            self.log_message("⏹️ Stopping scraping operation...")
            self.current_op_label.config(text="Stopping...", foreground="orange")
    
    def _scraping_worker(self):
        """Background worker for real scraping operations"""
        scraper = None
        api_client = None
        
        try:
            assignment_type = self.current_assignment["type"]
            
            # Update assignment status to in_progress
            self.config_manager.set_value("current_assignment", "status", "in_progress")
            self.config_manager.save_config()
            
            # Initialize API client
            api_key = self.config_manager.get_value("api_settings", "api_key")
            api_client = self._create_api_client(api_key)
            
            # Initialize scraper
            scraper = self._create_scraper()
            
            if assignment_type in ["indexing", "index_games"]:
                self._real_index_games(scraper, api_client)
            elif assignment_type in ["replayscraping", "collect_logs"]:
                self._real_replay_scraping(scraper, api_client)
            else:
                raise ValueError(f"Unknown assignment type: {assignment_type}")
            
            # Mark assignment as completed if not stopped
            if not self.should_stop:
                self.config_manager.set_value("current_assignment", "status", "completed")
                self.config_manager.save_config()
                
                self.frame.after(0, lambda: self.log_message("✅ Assignment completed successfully!"))
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error during scraping: {e}")
            self.frame.after(0, lambda: self.log_message(f"❌ Error during scraping: {error_msg}"))
            
            # Show error dialog for critical errors
            if "Authentication" in error_msg or "login" in error_msg.lower():
                self.frame.after(0, lambda: messagebox.showerror(
                    "Authentication Error", 
                    f"Authentication failed:\n{error_msg}\n\nPlease check your BGA credentials in Settings."
                ))
            elif "daily limit" in error_msg.lower() or "limit reached" in error_msg.lower():
                self.frame.after(0, lambda: messagebox.showwarning(
                    "Daily Limit Reached", 
                    f"Daily replay limit reached:\n{error_msg}\n\nPlease try again tomorrow."
                ))
            elif "API" in error_msg or "network" in error_msg.lower():
                self.frame.after(0, lambda: messagebox.showerror(
                    "Network Error", 
                    f"Network or API error:\n{error_msg}\n\nPlease check your internet connection."
                ))
        
        finally:
            # Clean up scraper
            if scraper:
                try:
                    scraper.close_browser()
                except:
                    pass
            
            # Clean up
            self.frame.after(0, self._scraping_finished)
    
    def _create_api_client(self, api_key):
        """Create API client instance"""
        from ..api_client import APIClient
        return APIClient(api_key)
    
    def _create_scraper(self):
        """Create scraper instance"""
        from ..scraper_wrapper import create_scraper_from_gui_config
        
        def progress_callback(message):
            self.frame.after(0, lambda: self.log_message(message))
        
        return create_scraper_from_gui_config(self.config_manager, progress_callback)
    
    def _real_index_games(self, scraper, api_client):
        """Real implementation of index games scraping"""
        player_id = self.current_assignment["details"]["player_id"]
        
        self.frame.after(0, lambda: self.log_message(f"🔍 Starting to index games for player {player_id}"))
        
        try:
            # Start browser and login
            self.frame.after(0, lambda: self.current_op_label.config(
                text="Starting browser and logging in...", foreground="blue"
            ))
            
            if not scraper.start_browser_and_login():
                raise RuntimeError("Failed to start browser and login")
            
            # Get already indexed games from API
            self.frame.after(0, lambda: self.current_op_label.config(
                text="Getting already indexed games...", foreground="blue"
            ))
            
            indexed_games = api_client.get_indexed_games_by_player(player_id)
            self.frame.after(0, lambda: self.log_message(f"Found {len(indexed_games)} already indexed games"))
            
            # Scrape player's game history
            self.frame.after(0, lambda: self.current_op_label.config(
                text=f"Scraping player {player_id} game history...", foreground="blue"
            ))
            
            games_data = scraper.scrape_player_game_history(player_id, max_clicks=1000)
            
            if not games_data:
                raise RuntimeError(f"No games found for player {player_id}")
            
            self.frame.after(0, lambda: self.log_message(f"Found {len(games_data)} total games for player {player_id}"))
            
            # Update total items based on actual games found
            new_games = [game for game in games_data if game['table_id'] not in indexed_games]
            self.total_items = len(new_games)
            self.frame.after(0, self.update_progress)
            
            self.frame.after(0, lambda: self.log_message(f"Processing {len(new_games)} new games (skipping {len(indexed_games)} already indexed)"))
            
            # Process each game individually
            for i, game_info in enumerate(new_games):
                if self.should_stop:
                    break
                
                table_id = game_info['table_id']
                
                self.frame.after(0, lambda tid=table_id: self.current_op_label.config(
                    text=f"Processing game {tid}", foreground="blue"
                ))
                
                try:
                    # Scrape table only (in memory)
                    result = scraper.scrape_table_only_memory(table_id, player_id)
                    
                    if result and result.get('success'):
                        game_mode = result.get('game_mode', 'Normal mode')
                        elo_data = result.get('elo_data', {})
                        version = result.get('version')
                        
                        # Convert EloData objects to dictionaries for JSON serialization
                        players_list = []
                        if elo_data:
                            for player_name, elo_obj in elo_data.items():
                                player_dict = {
                                    'player_name': elo_obj.player_name or player_name,
                                    'player_id': elo_obj.player_id,
                                    'position': elo_obj.position,
                                    'arena_points': elo_obj.arena_points,
                                    'arena_points_change': elo_obj.arena_points_change,
                                    'game_rank': elo_obj.game_rank,
                                    'game_rank_change': elo_obj.game_rank_change
                                }
                                players_list.append(player_dict)
                        
                        # Create game data structure for single game API
                        game_api_data = {
                            'table_id': table_id,
                            'raw_datetime': game_info['raw_datetime'],
                            'parsed_datetime': game_info['parsed_datetime'],
                            'game_mode': game_mode,
                            'version': version,
                            'player_perspective': player_id,
                            'scraped_at': result.get('scraped_at'),
                            'players': players_list,
                            'map': result.get('map'),
                            'prelude_on': result.get('prelude_on'),
                            'colonies_on': result.get('colonies_on'),
                            'corporate_era_on': result.get('corporate_era_on'),
                            'draft_on': result.get('draft_on'),
                            'beginners_corporations_on': result.get('beginners_corporations_on'),
                            'game_speed': result.get('game_speed')
                        }
                        
                        # Upload to API immediately
                        if api_client.update_single_game(game_api_data):
                            self.successful_items += 1
                            self.frame.after(0, lambda tid=table_id, mode=game_mode: 
                                           self.log_message(f"✅ Game {tid} ({mode}) indexed successfully"))
                        else:
                            self.failed_items += 1
                            self.frame.after(0, lambda tid=table_id: 
                                           self.log_message(f"❌ Failed to upload game {tid} to API"))
                    else:
                        self.failed_items += 1
                        self.frame.after(0, lambda tid=table_id: 
                                       self.log_message(f"❌ Failed to scrape game {tid}"))
                
                except Exception as e:
                    self.failed_items += 1
                    logger.error(f"Error processing game {table_id}: {e}")
                    self.frame.after(0, lambda tid=table_id, err=str(e): 
                                   self.log_message(f"❌ Error processing game {tid}: {err}"))
                
                self.completed_items += 1
                
                # Add delay between games
                request_delay = self.config_manager.get_value("scraping_settings", "request_delay")
                if request_delay > 0:
                    time.sleep(request_delay)
            
            # Summary
            if self.completed_items > 0:
                self.frame.after(0, lambda: self.log_message(
                    f"📊 Player {player_id}: {self.successful_items}/{self.completed_items} games indexed successfully"
                ))
            else:
                self.frame.after(0, lambda: self.log_message(f"ℹ️ No new games to process for player {player_id}"))
                
        except Exception as e:
            logger.error(f"Error in index games scraping: {e}")
            raise
    
    def _real_replay_scraping(self, scraper, api_client):
        """Real implementation of replay scraping"""
        assignment_type = self.current_assignment["type"]
        
        if assignment_type == "replayscraping":
            # Real API assignment format
            games = self.current_assignment["details"]["games"]
            player_perspective_id = self.current_assignment["details"]["player_perspective_id"]
            
            self.frame.after(0, lambda: self.log_message(f"📋 Starting to collect logs for {len(games)} games"))
            
            try:
                # Start browser and login
                self.frame.after(0, lambda: self.current_op_label.config(
                    text="Starting browser and logging in...", foreground="blue"
                ))
                
                if not scraper.start_browser_and_login():
                    raise RuntimeError("Failed to start browser and login")
                
                # Filter games to only process those not already completed
                games_to_process = self._get_games_to_process(games)
                
                if len(games_to_process) < len(games):
                    skipped_count = len(games) - len(games_to_process)
                    self.frame.after(0, lambda: self.log_message(f"📊 Skipping {skipped_count} already processed games"))
                
                # Update total items to reflect actual games to process
                # Only update total_items if we don't have existing progress
                if not self.existing_progress:
                    self.total_items = len(games_to_process)
                else:
                    # Keep the original total from the assignment when resuming
                    self.total_items = len(games)
                self.frame.after(0, self.update_progress)
                
                # Process each game
                for i, game in enumerate(games_to_process):
                    if self.should_stop:
                        break
                    
                    table_id = str(game.get("tableId", f"Unknown_{i}"))
                    version_id = str(game.get("versionId", ""))
                    
                    # Skip if already processed (double-check)
                    if self._is_game_already_processed(table_id):
                        self.frame.after(0, lambda tid=table_id: 
                                       self.log_message(f"⏭️ Skipping already processed game {tid}"))
                        continue
                    
                    self.frame.after(0, lambda tid=table_id: self.current_op_label.config(
                        text=f"Processing game {tid}", foreground="blue"
                    ))
                    
                    success = False
                    try:
                        # Get the correct player perspective for THIS specific game
                        game_player_perspective = str(game.get("playerPerspective"))
                        
                        # Build assignment metadata for this game using actual assignment data
                        assignment_metadata = {
                            'gameMode': game.get('gameMode', 'Arena mode'),
                            'versionId': version_id,
                            'players': game.get('players', []),  # Use the actual players array from assignment
                            'map': game.get('map'),
                            'preludeOn': game.get('preludeOn'),
                            'coloniesOn': game.get('coloniesOn'),
                            'corporateEraOn': game.get('corporateEraOn'),
                            'draftOn': game.get('draftOn'),
                            'beginnersCorporationsOn': game.get('beginnersCorporationsOn'),
                            'gameSpeed': game.get('gameSpeed'),
                            'playedAt': game.get('playedAt')
                        }
                        
                        # Scrape replay only with assignment metadata (more efficient)
                        parsed_game_data = scraper.scrape_replay_only_with_assignment_metadata(
                            table_id=table_id,
                            version_id=version_id,
                            player_perspective=game_player_perspective,
                            assignment_metadata=assignment_metadata
                        )
                        
                        # Check for daily limit reached
                        if parsed_game_data and parsed_game_data.get('daily_limit_reached'):
                            self.frame.after(0, lambda: self.log_message("🚫 Daily replay limit reached - stopping scraping"))
                            self.frame.after(0, lambda: self._handle_daily_limit_reached())
                            break  # Stop processing more games
                        
                        if parsed_game_data:
                            # Get BGA email for scrapedBy parameter
                            bga_email = self.config_manager.get_value("bga_credentials", "email", "")
                            
                            # Upload parsed game data to API via StoreGameLog
                            if api_client.store_game_log(parsed_game_data, bga_email):
                                success = True
                                self.successful_items += 1
                                self.frame.after(0, lambda tid=table_id: 
                                               self.log_message(f"✅ Collected and uploaded logs for game {tid}"))
                            else:
                                self.failed_items += 1
                                self.frame.after(0, lambda tid=table_id: 
                                               self.log_message(f"❌ Failed to upload logs for game {tid} to API"))
                        else:
                            self.failed_items += 1
                            self.frame.after(0, lambda tid=table_id: 
                                           self.log_message(f"❌ Failed to scrape and parse game {tid}"))
                    
                    except Exception as e:
                        self.failed_items += 1
                        error_msg = str(e)
                        
                        # Check for daily limit in exception message
                        if "daily limit" in error_msg.lower() or "limit reached" in error_msg.lower():
                            self.frame.after(0, lambda: self.log_message("🚫 Daily replay limit reached - stopping scraping"))
                            self.frame.after(0, lambda: self._handle_daily_limit_reached())
                            break  # Stop processing more games
                        
                        logger.error(f"Error processing game {table_id}: {e}")
                        self.frame.after(0, lambda tid=table_id, err=error_msg: 
                                       self.log_message(f"❌ Error processing game {tid}: {err}"))
                    
                    # Update progress tracking for this game
                    self._update_progress_tracking(table_id, success)
                    
                    self.completed_items += 1
                    
                    # Add delay between games
                    request_delay = self.config_manager.get_value("scraping_settings", "request_delay")
                    if request_delay > 0:
                        time.sleep(request_delay)
                
                # Summary
                if self.completed_items > 0:
                    self.frame.after(0, lambda: self.log_message(
                        f"📊 Replay scraping: {self.successful_items}/{self.completed_items} games processed successfully"
                    ))
                else:
                    self.frame.after(0, lambda: self.log_message("ℹ️ No games were processed"))
                    
            except Exception as e:
                logger.error(f"Error in replay scraping: {e}")
                raise
        else:
            # Legacy format (collect_logs) - use mock for now
            self._mock_collect_logs()
    
    def _mock_collect_logs(self):
        """Mock implementation of collect logs scraping (legacy format)"""
        table_ids = self.current_assignment["details"]["table_ids"]
        player_perspective = self.current_assignment["details"]["player_perspective"]
        
        self.frame.after(0, lambda: self.log_message(f"📋 Starting to collect logs for {len(table_ids)} games"))
        
        for i, table_id_combo in enumerate(table_ids):
            if self.should_stop:
                break
            
            # Simulate processing time (longer for log collection)
            time.sleep(random.uniform(1.0, 3.0))
            
            # Extract table ID from combo
            table_id = table_id_combo.split(':')[0]
            success = random.random() > 0.15  # 85% success rate
            
            if success:
                self.successful_items += 1
                self.frame.after(0, lambda tid=table_id: self.log_message(f"✅ Collected logs for game {tid}"))
            else:
                self.failed_items += 1
                self.frame.after(0, lambda tid=table_id: self.log_message(f"❌ Failed to collect logs for game {tid}"))
            
            self.completed_items += 1
            
            # Update current operation
            self.frame.after(0, lambda tid=table_id: self.current_op_label.config(
                text=f"Processing game {tid}", foreground="blue"
            ))
    
    def _handle_daily_limit_reached(self):
        """Handle daily limit reached scenario"""
        # Stop the scraping process
        self.should_stop = True
        
        # Update UI to show daily limit status
        self.current_op_label.config(text="Daily limit reached", foreground="red")
        
        # Save progress and mark assignment as paused
        self.config_manager.set_value("current_assignment", "status", "paused_daily_limit")
        self.config_manager.save_config()
        
        # Show user-friendly message
        elapsed_time = datetime.now() - self.start_time if self.start_time else None
        elapsed_str = str(elapsed_time).split('.')[0] if elapsed_time else "Unknown"
        
        message = "🚫 Daily Replay Limit Reached\n\n"
        message += "BGA has daily limits on replay access to prevent server overload.\n\n"
        message += "Progress saved:\n"
        message += f"• Processed: {self.completed_items} games\n"
        message += f"• Successful: {self.successful_items} games\n"
        message += f"• Time elapsed: {elapsed_str}\n\n"
        message += "You can resume this assignment in ~24 hours when your scraping limit has been reset."
        
        messagebox.showwarning("Daily Limit Reached", message)
    
    def _scraping_finished(self):
        """Clean up after scraping is finished"""
        self.is_scraping = False
        
        # Update UI
        self.get_assignment_btn.config(state="normal")
        self.start_btn.config(state="disabled")  # Keep disabled until new assignment
        self.stop_btn.config(state="disabled")
        
        # Determine the reason for stopping
        if self.should_stop:
            # Check if it was due to daily limit
            assignment_status = self.config_manager.get_value("current_assignment", "status")
            if assignment_status == "paused_daily_limit":
                self.current_op_label.config(text="Paused - Daily limit reached", foreground="red")
                self.log_message("🚫 Scraping paused due to daily replay limit")
            else:
                self.current_op_label.config(text="Stopped by user", foreground="orange")
                self.log_message("⏹️ Scraping stopped by user")
        else:
            self.current_op_label.config(text="Completed", foreground="green")
        
        # Refresh assignment status
        self.check_assignment()
        
        # Show completion summary (only if not stopped due to daily limit)
        assignment_status = self.config_manager.get_value("current_assignment", "status")
        if not self.should_stop or assignment_status != "paused_daily_limit":
            success_rate = (self.successful_items / max(self.completed_items, 1)) * 100
            elapsed_time = datetime.now() - self.start_time if self.start_time else None
            elapsed_str = str(elapsed_time).split('.')[0] if elapsed_time else "Unknown"
            
            if self.should_stop:
                title = "Scraping Stopped"
                summary = f"Scraping stopped by user.\n\n"
            else:
                title = "Scraping Complete"
                summary = f"Scraping completed successfully!\n\n"
            
            summary += f"Total processed: {self.completed_items}\n"
            summary += f"Successful: {self.successful_items}\n"
            summary += f"Failed: {self.failed_items}\n"
            summary += f"Success rate: {success_rate:.1f}%\n"
            summary += f"Time elapsed: {elapsed_str}"
            
            messagebox.showinfo(title, summary)
    
    def _update_timer(self):
        """Update the elapsed time display"""
        if self.is_scraping and self.start_time:
            elapsed = datetime.now() - self.start_time
            elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
            self.time_label.config(text=f"⏱️ Elapsed: {elapsed_str}")
            
            # Schedule next update
            self.frame.after(1000, self._update_timer)
    
    def update_progress(self):
        """Update progress indicators"""
        if self.total_items > 0:
            progress_percent = (self.completed_items / self.total_items) * 100
            self.progress_bar["value"] = progress_percent
            
            self.progress_label.config(
                text=f"{self.completed_items} / {self.total_items} ({progress_percent:.1f}%)"
            )
        else:
            self.progress_bar["value"] = 0
            self.progress_label.config(text="0 / 0 (0%)")
        
        # Update counters
        self.success_label.config(text=f"✅ Success: {self.successful_items}")
        self.failure_label.config(text=f"❌ Failed: {self.failed_items}")
        
        # Schedule next update if scraping
        if self.is_scraping:
            self.frame.after(500, self.update_progress)
    
    def log_message(self, message):
        """Add a message to the activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        self.log_text.config(state=tk.DISABLED)
    
    def clear_log(self):
        """Clear the activity log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _update_start_button_text(self):
        """Update start button text based on existing progress"""
        if self.existing_progress:
            completed = len(self.existing_progress.get("completed_games", []))
            failed = len(self.existing_progress.get("failed_games", []))
            total_processed = completed + failed
            if total_processed > 0:
                self.start_btn.config(text=f"🔄 Resume Scraping ({total_processed} done)")
            else:
                self.start_btn.config(text="🚀 Start Scraping")
        else:
            self.start_btn.config(text="🚀 Start Scraping")
    
    def _restore_progress_from_existing(self):
        """Restore progress counters from existing progress data"""
        if self.existing_progress:
            counters = self.existing_progress.get("counters", {})
            self.completed_items = counters.get("completed_items", 0)
            self.successful_items = counters.get("successful_items", 0)
            self.failed_items = counters.get("failed_items", 0)
            
            # Update total items if available
            if counters.get("total_items", 0) > 0:
                self.total_items = counters["total_items"]
            
            self.log_message(f"📊 Restored progress: {self.successful_items} successful, {self.failed_items} failed")
    
    def _initialize_progress_tracking(self):
        """Initialize progress tracking for the current assignment"""
        if not self.current_assignment_id:
            return
        
        # Initialize progress data if it doesn't exist
        if not self.existing_progress:
            from datetime import datetime
            self.existing_progress = {
                "completed_games": [],
                "failed_games": [],
                "last_processed_index": -1,
                "counters": {
                    "total_items": self.total_items,
                    "completed_items": 0,
                    "successful_items": 0,
                    "failed_items": 0
                },
                "timestamps": {
                    "started_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
            self.config_manager.save_assignment_progress(self.current_assignment_id, self.existing_progress)
        else:
            # Update total items in existing progress
            self.existing_progress["counters"]["total_items"] = self.total_items
            self.config_manager.save_assignment_progress(self.current_assignment_id, self.existing_progress)
    
    def _update_progress_tracking(self, table_id: str, success: bool):
        """Update progress tracking for a completed game"""
        if self.current_assignment_id:
            self.config_manager.update_game_completion(self.current_assignment_id, table_id, success)
            # Reload progress to get updated data
            self.existing_progress = self.config_manager.load_assignment_progress(self.current_assignment_id)
    
    def _is_game_already_processed(self, table_id: str) -> bool:
        """Check if a game has already been processed"""
        if not self.existing_progress:
            return False
        
        table_id_str = str(table_id)
        completed_games = self.existing_progress.get("completed_games", [])
        failed_games = self.existing_progress.get("failed_games", [])
        
        return table_id_str in completed_games or table_id_str in failed_games
    
    def _get_games_to_process(self, all_games):
        """Filter games to only include those not already processed"""
        if not self.existing_progress:
            return all_games
        
        completed_games = set(self.existing_progress.get("completed_games", []))
        failed_games = set(self.existing_progress.get("failed_games", []))
        processed_games = completed_games | failed_games
        
        # Filter out already processed games
        games_to_process = []
        for game in all_games:
            if isinstance(game, dict):
                table_id = str(game.get("tableId", ""))
            else:
                # Handle other game data formats
                table_id = str(getattr(game, 'table_id', ''))
            
            if table_id and table_id not in processed_games:
                games_to_process.append(game)
        
        return games_to_process
    
    def stop_scraping_if_running(self):
        """Stop scraping if it's currently running (called on app close)"""
        if self.is_scraping:
            self.should_stop = True
            if self.scraping_thread and self.scraping_thread.is_alive():
                self.scraping_thread.join(timeout=2.0)  # Wait up to 2 seconds
    
    def _validate_game_count(self, value):
        """Validate game count input"""
        # Clear any existing error
        self.game_count_error_label.pack_forget()
        
        # Allow empty value
        if not value:
            return True
        
        try:
            # Check if it's a valid integer
            count = int(value)
            
            # Check range
            if count < 1 or count > 200:
                self._show_game_count_error("Must be between 1 and 200")
                return False
            
            return True
        except ValueError:
            self._show_game_count_error("Must be a valid number")
            return False
    
    def _show_game_count_error(self, message):
        """Show game count validation error"""
        self.game_count_error_label.config(text=message)
        self.game_count_error_label.pack(pady=(5, 0))
    
    def _load_game_count(self):
        """Load saved game count from config"""
        saved_count = self.config_manager.get_value("assignment_settings", "game_count", "")
        self.game_count_var.set(str(saved_count) if saved_count else "")
    
    def _save_game_count(self):
        """Save game count to config"""
        value = self.game_count_var.get().strip()
        self.config_manager.set_value("assignment_settings", "game_count", value)
        self.config_manager.save_config()
    
    def _get_validated_game_count(self):
        """Get validated game count or None if invalid/empty"""
        value = self.game_count_var.get().strip()
        
        if not value:
            return None
        
        try:
            count = int(value)
            if 1 <= count <= 200:
                return count
            else:
                self._show_game_count_error("Must be between 1 and 200")
                return False  # Invalid
        except ValueError:
            self._show_game_count_error("Must be a valid number")
            return False  # Invalid
