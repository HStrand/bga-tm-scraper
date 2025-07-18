"""
Download Tab for BGA TM Scraper GUI
Handles downloading scraped data from the central registry
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import random
import os
from datetime import datetime, timedelta


class DownloadTab:
    """Download tab for retrieving scraped data"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Download state
        self.is_downloading = False
        self.download_thread = None
        self.should_stop = False
        
        # Progress tracking
        self.total_size = 0
        self.downloaded_size = 0
        self.download_speed = 0
        self.start_time = None
        
        # Create the UI
        self.create_widgets()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Download Data", 
                               font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_text = """Download scraped game data from the central registry.
All data is packaged in a convenient ZIP file for analysis and research."""
        
        desc_label = ttk.Label(main_frame, text=desc_text, justify="center")
        desc_label.pack(pady=(0, 30))
        
        # Download options frame
        options_frame = ttk.LabelFrame(main_frame, text="Download Options", padding=15)
        options_frame.pack(fill="x", pady=(0, 20))
        
        # Dataset selection
        dataset_frame = ttk.Frame(options_frame)
        dataset_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(dataset_frame, text="Dataset:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.dataset_var = tk.StringVar(value="complete")
        
        complete_rb = ttk.Radiobutton(
            dataset_frame,
            text="Complete Dataset (All games and logs)",
            variable=self.dataset_var,
            value="complete"
        )
        complete_rb.pack(anchor="w", pady=2)
        
        games_only_rb = ttk.Radiobutton(
            dataset_frame,
            text="Games Index Only (Metadata only, smaller file)",
            variable=self.dataset_var,
            value="games_only"
        )
        games_only_rb.pack(anchor="w", pady=2)
        
        logs_only_rb = ttk.Radiobutton(
            dataset_frame,
            text="Game Logs Only (Detailed replay data)",
            variable=self.dataset_var,
            value="logs_only"
        )
        logs_only_rb.pack(anchor="w", pady=2)
        
        # Format selection
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(format_frame, text="Format:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.format_var = tk.StringVar(value="json")
        
        json_rb = ttk.Radiobutton(
            format_frame,
            text="JSON (Structured data, recommended)",
            variable=self.format_var,
            value="json"
        )
        json_rb.pack(anchor="w", pady=2)
        
        csv_rb = ttk.Radiobutton(
            format_frame,
            text="CSV (Spreadsheet compatible, flattened data)",
            variable=self.format_var,
            value="csv"
        )
        csv_rb.pack(anchor="w", pady=2)
        
        # Filters section (placeholder for future)
        filters_frame = ttk.Frame(options_frame)
        filters_frame.pack(fill="x")
        
        ttk.Label(filters_frame, text="Filters (Coming Soon):", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.date_filter_var = tk.BooleanVar()
        date_cb = ttk.Checkbutton(
            filters_frame,
            text="Filter by date range",
            variable=self.date_filter_var,
            state="disabled"
        )
        date_cb.pack(anchor="w", pady=2)
        
        self.player_filter_var = tk.BooleanVar()
        player_cb = ttk.Checkbutton(
            filters_frame,
            text="Filter by specific players",
            variable=self.player_filter_var,
            state="disabled"
        )
        player_cb.pack(anchor="w", pady=2)
        
        # Download location frame
        location_frame = ttk.LabelFrame(main_frame, text="Download Location", padding=15)
        location_frame.pack(fill="x", pady=(0, 20))
        
        location_input_frame = ttk.Frame(location_frame)
        location_input_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(location_input_frame, text="Save to:").pack(side="left")
        
        self.location_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        location_entry = ttk.Entry(location_input_frame, textvariable=self.location_var)
        location_entry.pack(side="left", fill="x", expand=True, padx=(10, 5))
        
        browse_btn = ttk.Button(
            location_input_frame,
            text="Browse...",
            command=self.browse_location
        )
        browse_btn.pack(side="right")
        
        # File info
        self.file_info_label = ttk.Label(
            location_frame,
            text="File will be saved as: tm_scraper_data_YYYYMMDD_HHMMSS.zip",
            foreground="gray",
            font=("TkDefaultFont", 9)
        )
        self.file_info_label.pack(anchor="w")
        
        # Download controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill="x", pady=(0, 20))
        
        # Download button
        self.download_btn = ttk.Button(
            controls_frame,
            text="💾 Start Download",
            command=self.start_download,
            style="Accent.TButton"
        )
        self.download_btn.pack(side="left", padx=(0, 10))
        
        # Cancel button
        self.cancel_btn = ttk.Button(
            controls_frame,
            text="❌ Cancel Download",
            command=self.cancel_download,
            state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=(0, 10))
        
        # Get info button
        info_btn = ttk.Button(
            controls_frame,
            text="ℹ️ Dataset Info",
            command=self.show_dataset_info
        )
        info_btn.pack(side="left")
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Download Progress", padding=15)
        progress_frame.pack(fill="both", expand=True)
        
        # Progress info
        progress_info_frame = ttk.Frame(progress_frame)
        progress_info_frame.pack(fill="x", pady=(0, 10))
        
        self.progress_label = ttk.Label(progress_info_frame, text="Ready to download")
        self.progress_label.pack(side="left")
        
        self.speed_label = ttk.Label(progress_info_frame, text="")
        self.speed_label.pack(side="right")
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 15))
        
        # Download stats
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill="x", pady=(0, 10))
        
        self.size_label = ttk.Label(stats_frame, text="Size: 0 MB / 0 MB")
        self.size_label.pack(side="left")
        
        self.time_label = ttk.Label(stats_frame, text="")
        self.time_label.pack(side="right")
        
        # Status log
        log_frame = ttk.Frame(progress_frame)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        ttk.Label(log_frame, text="Status Log:", font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
        
        # Log text widget
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill="both", expand=True, pady=(5, 0))
        
        self.log_text = tk.Text(
            log_container,
            height=6,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#f8f8f8"
        )
        
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Initial log message
        self.log_message("Ready to download data from the central registry")
    
    def browse_location(self):
        """Browse for download location"""
        folder = filedialog.askdirectory(
            title="Select download location",
            initialdir=self.location_var.get()
        )
        if folder:
            self.location_var.set(folder)
    
    def show_dataset_info(self):
        """Show information about available datasets"""
        info_text = """Dataset Information:

Complete Dataset:
• All indexed games with metadata
• Full game logs with move-by-move data
• Player statistics and ELO data
• Estimated size: 500-2000 MB
• Best for comprehensive analysis

Games Index Only:
• Game metadata and basic information
• Player lists and ELO changes
• No detailed move data
• Estimated size: 50-200 MB
• Good for statistical analysis

Game Logs Only:
• Detailed replay data
• Move-by-move game progression
• Resource and VP tracking
• Estimated size: 400-1800 MB
• Best for game mechanics analysis

Format Options:
• JSON: Structured, hierarchical data
• CSV: Flattened data for spreadsheets

Note: Actual file sizes depend on the amount of data available in the registry."""
        
        messagebox.showinfo("Dataset Information", info_text)
    
    def start_download(self):
        """Start the download process"""
        if self.is_downloading:
            return
        
        # Validate download location
        location = self.location_var.get()
        if not location or not os.path.exists(location):
            messagebox.showerror("Invalid Location", "Please select a valid download location.")
            return
        
        # Check if location is writable
        if not os.access(location, os.W_OK):
            messagebox.showerror("Permission Error", "Cannot write to the selected location.")
            return
        
        # Get dataset info
        dataset_type = self.dataset_var.get()
        format_type = self.format_var.get()
        
        dataset_names = {
            "complete": "Complete Dataset",
            "games_only": "Games Index Only",
            "logs_only": "Game Logs Only"
        }
        
        # Confirm download
        dataset_name = dataset_names[dataset_type]
        if not messagebox.askyesno("Start Download", 
                                  f"Download {dataset_name} in {format_type.upper()} format?\n\n"
                                  f"This may take several minutes depending on file size."):
            return
        
        # Initialize download
        self.is_downloading = True
        self.should_stop = False
        self.start_time = datetime.now()
        
        # Update UI
        self.download_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tm_scraper_{dataset_type}_{format_type}_{timestamp}.zip"
        self.download_path = os.path.join(location, filename)
        
        # Mock file sizes (in MB)
        size_ranges = {
            "complete": (500, 2000),
            "games_only": (50, 200),
            "logs_only": (400, 1800)
        }
        
        self.total_size = random.randint(*size_ranges[dataset_type])
        self.downloaded_size = 0
        
        self.log_message(f"Starting download of {dataset_name}")
        self.log_message(f"File: {filename}")
        self.log_message(f"Estimated size: {self.total_size} MB")
        
        # Start download in background thread
        self.download_thread = threading.Thread(target=self._download_worker, daemon=True)
        self.download_thread.start()
        
        # Start progress update timer
        self._update_progress_timer()
    
    def cancel_download(self):
        """Cancel the download process"""
        if not self.is_downloading:
            return
        
        if messagebox.askyesno("Cancel Download", "Are you sure you want to cancel the download?"):
            self.should_stop = True
            self.log_message("Cancelling download...")
    
    def _download_worker(self):
        """Background worker for download (mock implementation)"""
        try:
            # Simulate download with progress updates
            chunk_size = 5  # MB per chunk
            chunks = self.total_size // chunk_size
            
            for i in range(chunks + 1):
                if self.should_stop:
                    break
                
                # Simulate download time
                time.sleep(random.uniform(0.5, 2.0))
                
                # Update progress
                chunk_downloaded = min(chunk_size, self.total_size - self.downloaded_size)
                self.downloaded_size += chunk_downloaded
                
                # Calculate speed
                if self.start_time:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    if elapsed > 0:
                        self.download_speed = self.downloaded_size / elapsed
                
                # Log progress occasionally
                if i % 5 == 0 or self.downloaded_size >= self.total_size:
                    progress_percent = (self.downloaded_size / self.total_size) * 100
                    self.frame.after(0, lambda p=progress_percent: self.log_message(f"Downloaded {p:.1f}%"))
                
                if self.downloaded_size >= self.total_size:
                    break
            
            # Simulate file finalization
            if not self.should_stop:
                self.frame.after(0, lambda: self.log_message("Finalizing download..."))
                time.sleep(1)
                
                # Create a placeholder file (in real implementation, this would be the actual download)
                try:
                    with open(self.download_path, 'w') as f:
                        f.write(f"# BGA TM Scraper Data Export\n")
                        f.write(f"# Generated: {datetime.now()}\n")
                        f.write(f"# Dataset: {self.dataset_var.get()}\n")
                        f.write(f"# Format: {self.format_var.get()}\n")
                        f.write(f"# This is a placeholder file for the GUI demo\n")
                    
                    self.frame.after(0, lambda: self.log_message("✅ Download completed successfully!"))
                    self.frame.after(0, self._download_completed)
                    
                except Exception as e:
                    self.frame.after(0, lambda: self.log_message(f"❌ Error saving file: {str(e)}"))
            
        except Exception as e:
            self.frame.after(0, lambda: self.log_message(f"❌ Download error: {str(e)}"))
        
        finally:
            # Clean up
            self.frame.after(0, self._download_finished)
    
    def _download_completed(self):
        """Handle successful download completion"""
        # Show completion dialog
        message = f"Download completed successfully!\n\n"
        message += f"File saved to:\n{self.download_path}\n\n"
        message += f"Size: {self.total_size} MB\n"
        
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            elapsed_str = str(elapsed).split('.')[0]
            message += f"Time: {elapsed_str}\n"
        
        message += f"Speed: {self.download_speed:.1f} MB/s"
        
        result = messagebox.askquestion(
            "Download Complete", 
            message + "\n\nWould you like to open the download folder?",
            icon="question"
        )
        
        if result == "yes":
            # Open the download folder
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(os.path.dirname(self.download_path))
                elif os.name == 'posix':  # macOS and Linux
                    os.system(f'open "{os.path.dirname(self.download_path)}"')
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder:\n{str(e)}")
    
    def _download_finished(self):
        """Clean up after download is finished"""
        self.is_downloading = False
        
        # Update UI
        self.download_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        
        if self.should_stop:
            self.progress_label.config(text="Download cancelled")
            self.log_message("❌ Download cancelled by user")
            
            # Clean up partial file
            if hasattr(self, 'download_path') and os.path.exists(self.download_path):
                try:
                    os.remove(self.download_path)
                except:
                    pass
        else:
            self.progress_label.config(text="Download completed")
    
    def _update_progress_timer(self):
        """Update progress indicators"""
        if self.is_downloading:
            # Update progress bar
            if self.total_size > 0:
                progress_percent = (self.downloaded_size / self.total_size) * 100
                self.progress_bar["value"] = progress_percent
                
                self.progress_label.config(
                    text=f"Downloading... {progress_percent:.1f}%"
                )
            
            # Update size info
            self.size_label.config(
                text=f"Size: {self.downloaded_size:.1f} MB / {self.total_size:.1f} MB"
            )
            
            # Update speed info
            if self.download_speed > 0:
                self.speed_label.config(text=f"Speed: {self.download_speed:.1f} MB/s")
                
                # Calculate ETA
                remaining_mb = self.total_size - self.downloaded_size
                if remaining_mb > 0:
                    eta_seconds = remaining_mb / self.download_speed
                    eta_str = str(timedelta(seconds=int(eta_seconds)))
                    self.time_label.config(text=f"ETA: {eta_str}")
            
            # Schedule next update
            self.frame.after(1000, self._update_progress_timer)
        else:
            # Final update
            self.progress_bar["value"] = 100 if not self.should_stop else 0
            self.speed_label.config(text="")
            self.time_label.config(text="")
    
    def log_message(self, message):
        """Add a message to the status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        self.log_text.config(state=tk.DISABLED)
