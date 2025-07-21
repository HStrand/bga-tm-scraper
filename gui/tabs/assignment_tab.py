"""
Assignment Tab for BGA TM Scraper GUI
Handles getting scraping assignments from the API (with mock implementation)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
from datetime import datetime


class AssignmentTab:
    """Assignment tab for getting scraping tasks"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Current assignment data
        self.current_assignment = None
        
        # Create the UI
        self.create_widgets()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Get Scraping Assignment", 
                               font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_text = """Get your next scraping assignment from the central registry.
You will be assigned either to index games or collect game logs based on current needs."""
        
        desc_label = ttk.Label(main_frame, text=desc_text, justify="center")
        desc_label.pack(pady=(0, 30))
        
        # Get Assignment Button
        self.get_assignment_btn = ttk.Button(
            main_frame, 
            text="🎯 Get New Assignment", 
            command=self.get_assignment,
            style="Accent.TButton"
        )
        self.get_assignment_btn.pack(pady=10)
        
        # Assignment Display Frame
        self.assignment_frame = ttk.LabelFrame(main_frame, text="Current Assignment", padding=15)
        self.assignment_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        # No assignment message (initially shown)
        self.no_assignment_label = ttk.Label(
            self.assignment_frame, 
            text="No assignment yet. Click 'Get New Assignment' to receive your task.",
            foreground="gray",
            font=("TkDefaultFont", 10, "italic")
        )
        self.no_assignment_label.pack(expand=True)
        
        # Assignment details frame (initially hidden)
        self.details_frame = ttk.Frame(self.assignment_frame)
        
        # Assignment type
        self.type_label = ttk.Label(self.details_frame, text="", font=("TkDefaultFont", 12, "bold"))
        self.type_label.pack(anchor="w", pady=(0, 10))
        
        # Assignment description
        self.desc_label = ttk.Label(self.details_frame, text="", justify="left")
        self.desc_label.pack(anchor="w", pady=(0, 10))
        
        # Assignment details
        self.details_text = tk.Text(
            self.details_frame, 
            height=8, 
            width=60, 
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#f0f0f0"
        )
        self.details_text.pack(fill="both", expand=True, pady=(0, 10))
        
        # Assignment actions frame
        self.actions_frame = ttk.Frame(self.details_frame)
        self.actions_frame.pack(fill="x", pady=(10, 0))
        
        # Accept assignment button
        self.accept_btn = ttk.Button(
            self.actions_frame,
            text="✅ Accept Assignment",
            command=self.accept_assignment,
            style="Accent.TButton"
        )
        self.accept_btn.pack(side="left", padx=(0, 10))
        
        # Decline assignment button
        self.decline_btn = ttk.Button(
            self.actions_frame,
            text="❌ Get Different Assignment",
            command=self.decline_assignment
        )
        self.decline_btn.pack(side="left")
        
        # Assignment status
        self.status_label = ttk.Label(self.actions_frame, text="", foreground="green")
        self.status_label.pack(side="right")
    
    def get_assignment(self):
        """Get a new assignment from the API (mock implementation)"""
        # Disable button during request
        self.get_assignment_btn.config(state="disabled", text="Getting assignment...")
        self.frame.update()
        
        # Simulate API delay
        self.frame.after(1500, self._process_assignment)
    
    def _process_assignment(self):
        """Process the assignment response (mock)"""
        try:
            # Mock assignment generation
            assignment_types = ["index_games", "collect_logs"]
            assignment_type = random.choice(assignment_types)
            
            if assignment_type == "index_games":
                self.current_assignment = self._generate_index_assignment()
            else:
                self.current_assignment = self._generate_logs_assignment()
            
            # Show assignment
            self._display_assignment()
            
            # Re-enable button
            self.get_assignment_btn.config(state="normal", text="🎯 Get New Assignment")
            
        except Exception as e:
            messagebox.showerror("Assignment Error", f"Failed to get assignment:\n{str(e)}")
            self.get_assignment_btn.config(state="normal", text="🎯 Get New Assignment")
    
    def _generate_index_assignment(self):
        """Generate a mock index games assignment"""
        # Mock player IDs
        player_ids = [
            "86296239", "12345678", "87654321", "11223344", "99887766"
        ]
        
        selected_player = random.choice(player_ids)
        
        return {
            "type": "index_games",
            "title": "🔍 Index Games Assignment",
            "description": "You have been assigned to index games for a specific player.",
            "details": {
                "player_id": selected_player,
                "player_name": f"Player_{selected_player}",
                "estimated_games": random.randint(50, 300),
                "priority": random.choice(["Normal", "High"]),
                "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "instructions": [
                "1. The scraper will automatically load the player's game history",
                "2. All Arena mode games will be identified and indexed",
                "3. Game metadata will be extracted and uploaded to the registry",
                "4. Progress will be tracked and reported in real-time",
                "5. You can monitor progress in the 'Start Scraping' tab"
            ]
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
            "description": "You have been assigned to collect detailed game logs for indexed games.",
            "details": {
                "table_count": table_count,
                "player_perspective": player_perspective,
                "table_ids": table_ids,
                "priority": random.choice(["Normal", "High"]),
                "assigned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "instructions": [
                "1. The scraper will process each table ID in the assignment",
                "2. Replay data will be downloaded and parsed",
                "3. Complete game logs with move-by-move data will be generated",
                "4. Parsed data will be uploaded to the central registry",
                "5. Progress will be tracked for each game processed"
            ]
        }
    
    def _display_assignment(self):
        """Display the current assignment in the UI"""
        if not self.current_assignment:
            return
        
        # Hide no assignment message
        self.no_assignment_label.pack_forget()
        
        # Show details frame
        self.details_frame.pack(fill="both", expand=True)
        
        # Update assignment type and description
        self.type_label.config(text=self.current_assignment["title"])
        self.desc_label.config(text=self.current_assignment["description"])
        
        # Update details text
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        
        details = self.current_assignment["details"]
        instructions = self.current_assignment["instructions"]
        
        # Format assignment details
        details_text = "Assignment Details:\n"
        details_text += "=" * 50 + "\n\n"
        
        if self.current_assignment["type"] == "index_games":
            details_text += f"Player ID: {details['player_id']}\n"
            details_text += f"Player Name: {details['player_name']}\n"
        else:
            details_text += f"Table Count: {details['table_count']}\n"
            details_text += f"Player Perspective: {details['player_perspective']}\n"
            details_text += f"Sample Table IDs: {', '.join(details['table_ids'][:5])}...\n"
        
        details_text += f"Priority: {details['priority']}\n"
        details_text += f"Assigned At: {details['assigned_at']}\n\n"
        
        details_text += "Instructions:\n"
        details_text += "=" * 50 + "\n"
        for instruction in instructions:
            details_text += f"{instruction}\n"
        
        self.details_text.insert(1.0, details_text)
        self.details_text.config(state=tk.DISABLED)
        
        # Clear status
        self.status_label.config(text="")
    
    def accept_assignment(self):
        """Accept the current assignment"""
        if not self.current_assignment:
            return
        
        # Show confirmation
        assignment_type = "Index Games" if self.current_assignment["type"] == "index_games" else "Collect Logs"
        
        if messagebox.askyesno("Accept Assignment", 
                              f"Accept this {assignment_type} assignment?\n\n"
                              "You can start scraping in the 'Start Scraping' tab."):
            
            self.status_label.config(text="✅ Assignment Accepted!", foreground="green")
            
            # Disable accept button
            self.accept_btn.config(state="disabled")
            
            # Store assignment in config for the scraping tab to use
            self.config_manager.set_value("current_assignment", "data", self.current_assignment)
            self.config_manager.set_value("current_assignment", "status", "accepted")
            self.config_manager.save_config()
            
            # Show success message
            messagebox.showinfo("Assignment Accepted", 
                               "Assignment accepted successfully!\n\n"
                               "Go to the 'Start Scraping' tab to begin processing.")
    
    def decline_assignment(self):
        """Decline the current assignment and get a new one"""
        if messagebox.askyesno("Decline Assignment", 
                              "Decline this assignment and get a different one?"):
            
            self.status_label.config(text="Getting new assignment...", foreground="orange")
            
            # Clear current assignment
            self.current_assignment = None
            
            # Hide details and show no assignment message
            self.details_frame.pack_forget()
            self.no_assignment_label.pack(expand=True)
            
            # Get new assignment after a short delay
            self.frame.after(1000, self.get_assignment)
    
    def refresh_assignment_status(self):
        """Refresh assignment status (called when tab is selected)"""
        # Check if there's a current assignment in progress
        assignment_data = self.config_manager.get_value("current_assignment", "data")
        assignment_status = self.config_manager.get_value("current_assignment", "status")
        
        if assignment_data and assignment_status == "accepted":
            self.current_assignment = assignment_data
            self._display_assignment()
            self.status_label.config(text="✅ Assignment Accepted!", foreground="green")
            self.accept_btn.config(state="disabled")
        elif assignment_data and assignment_status == "completed":
            self.status_label.config(text="✅ Assignment Completed!", foreground="blue")
            # Could show completion details here
