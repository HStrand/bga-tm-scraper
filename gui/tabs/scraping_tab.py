"""
Scraping Tab for BGA TM Scraper GUI
Handles the actual scraping operations with progress tracking
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
from datetime import datetime


class ScrapingTab:
    """Scraping tab for running scraping operations"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
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
        
        # Create the UI
        self.create_widgets()
        
        # Check for existing assignment
        self.check_assignment()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Start Scraping", 
                               font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Assignment status frame
        self.assignment_status_frame = ttk.LabelFrame(main_frame, text="Assignment Status", padding=10)
        self.assignment_status_frame.pack(fill="x", pady=(0, 20))
        
        self.assignment_status_label = ttk.Label(
            self.assignment_status_frame,
            text="No assignment loaded. Please get an assignment first.",
            foreground="orange"
        )
        self.assignment_status_label.pack()
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=(0, 20))
        
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
        self.stop_btn.pack(side="left", padx=(0, 10))
        
        # Refresh assignment button
        self.refresh_btn = ttk.Button(
            control_frame,
            text="🔄 Refresh Assignment",
            command=self.check_assignment
        )
        self.refresh_btn.pack(side="left")
        
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
    
    def check_assignment(self):
        """Check for current assignment and update UI"""
        assignment_data = self.config_manager.get_value("current_assignment", "data")
        assignment_status = self.config_manager.get_value("current_assignment", "status")
        
        if assignment_data and assignment_status == "accepted":
            # Show assignment details
            assignment_type = "Index Games" if assignment_data["type"] == "index_games" else "Collect Logs"
            
            if assignment_data["type"] == "index_games":
                details = assignment_data["details"]
                status_text = f"✅ {assignment_type} - Player: {details['player_id']} ({details['estimated_games']} games)"
            else:
                details = assignment_data["details"]
                status_text = f"✅ {assignment_type} - {details['table_count']} tables"
            
            self.assignment_status_label.config(text=status_text, foreground="green")
            self.start_btn.config(state="normal")
            
            # Store assignment for scraping
            self.current_assignment = assignment_data
            
        elif assignment_data and assignment_status == "completed":
            self.assignment_status_label.config(
                text="✅ Assignment completed! Get a new assignment to continue.",
                foreground="blue"
            )
            self.start_btn.config(state="disabled")
            
        else:
            self.assignment_status_label.config(
                text="No assignment loaded. Please get an assignment first.",
                foreground="orange"
            )
            self.start_btn.config(state="disabled")
            self.current_assignment = None
    
    def start_scraping(self):
        """Start the scraping process"""
        if not hasattr(self, 'current_assignment') or not self.current_assignment:
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
        
        # Confirm start
        assignment_type = "Index Games" if self.current_assignment["type"] == "index_games" else "Collect Logs"
        if not messagebox.askyesno("Start Scraping", 
                                  f"Start {assignment_type} scraping?\n\n"
                                  "This process may take a while to complete."):
            return
        
        # Initialize scraping
        self.is_scraping = True
        self.should_stop = False
        self.start_time = datetime.now()
        
        # Update UI
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.refresh_btn.config(state="disabled")
        
        # Initialize progress
        if self.current_assignment["type"] == "index_games":
            self.total_items = self.current_assignment["details"]["estimated_games"]
        else:
            self.total_items = self.current_assignment["details"]["table_count"]
        
        self.completed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        
        self.update_progress()
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
        """Background worker for scraping (mock implementation)"""
        try:
            assignment_type = self.current_assignment["type"]
            
            if assignment_type == "index_games":
                self._mock_index_games()
            else:
                self._mock_collect_logs()
            
            # Mark assignment as completed if not stopped
            if not self.should_stop:
                self.config_manager.set_value("current_assignment", "status", "completed")
                self.config_manager.save_config()
                
                self.frame.after(0, lambda: self.log_message("✅ Assignment completed successfully!"))
            
        except Exception as e:
            self.frame.after(0, lambda: self.log_message(f"❌ Error during scraping: {str(e)}"))
        
        finally:
            # Clean up
            self.frame.after(0, self._scraping_finished)
    
    def _mock_index_games(self):
        """Mock implementation of index games scraping"""
        player_id = self.current_assignment["details"]["player_id"]
        estimated_games = self.current_assignment["details"]["estimated_games"]
        
        self.frame.after(0, lambda: self.log_message(f"🔍 Starting to index games for player {player_id}"))
        
        for i in range(estimated_games):
            if self.should_stop:
                break
            
            # Simulate processing time
            time.sleep(random.uniform(0.5, 2.0))
            
            # Mock game processing
            table_id = random.randint(600000000, 700000000)
            success = random.random() > 0.1  # 90% success rate
            
            if success:
                self.successful_items += 1
                self.frame.after(0, lambda tid=table_id: self.log_message(f"✅ Indexed game {tid}"))
            else:
                self.failed_items += 1
                self.frame.after(0, lambda tid=table_id: self.log_message(f"❌ Failed to index game {tid}"))
            
            self.completed_items += 1
            
            # Update current operation
            self.frame.after(0, lambda tid=table_id: self.current_op_label.config(
                text=f"Processing game {tid}", foreground="blue"
            ))
    
    def _mock_collect_logs(self):
        """Mock implementation of collect logs scraping"""
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
    
    def _scraping_finished(self):
        """Clean up after scraping is finished"""
        self.is_scraping = False
        
        # Update UI
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.refresh_btn.config(state="normal")
        
        if self.should_stop:
            self.current_op_label.config(text="Stopped by user", foreground="orange")
            self.log_message("⏹️ Scraping stopped by user")
        else:
            self.current_op_label.config(text="Completed", foreground="green")
        
        # Refresh assignment status
        self.check_assignment()
        
        # Show completion summary
        if not self.should_stop:
            success_rate = (self.successful_items / max(self.completed_items, 1)) * 100
            elapsed_time = datetime.now() - self.start_time if self.start_time else None
            elapsed_str = str(elapsed_time).split('.')[0] if elapsed_time else "Unknown"
            
            summary = f"Scraping completed!\n\n"
            summary += f"Total processed: {self.completed_items}\n"
            summary += f"Successful: {self.successful_items}\n"
            summary += f"Failed: {self.failed_items}\n"
            summary += f"Success rate: {success_rate:.1f}%\n"
            summary += f"Time elapsed: {elapsed_str}"
            
            messagebox.showinfo("Scraping Complete", summary)
    
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
    
    def stop_scraping_if_running(self):
        """Stop scraping if it's currently running (called on app close)"""
        if self.is_scraping:
            self.should_stop = True
            if self.scraping_thread and self.scraping_thread.is_alive():
                self.scraping_thread.join(timeout=2.0)  # Wait up to 2 seconds
