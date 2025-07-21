"""
Download Tab for BGA TM Scraper GUI
Handles downloading the complete dataset from Google Drive
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import subprocess
from datetime import datetime, timedelta


class DownloadTab:
    """Download tab for retrieving the complete dataset from Google Drive"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Google Drive file configuration
        self.file_id = "1DSaPGKnp196yY3PhZ7gSFHdUOmmc-Jxu"
        self.file_url = f"https://drive.google.com/uc?id={self.file_id}"
        
        # Download state
        self.is_downloading = False
        self.download_thread = None
        self.should_stop = False
        
        # Progress tracking
        self.total_size = 0
        self.downloaded_size = 0
        self.download_speed = 0
        self.start_time = None
        self.last_update_time = None
        self.last_downloaded_size = 0
        
        # Create the UI
        self.create_widgets()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Download Complete Dataset", 
                               font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_text = """Download the complete BGA Terraforming Mars dataset.
This includes all indexed games with metadata and detailed game logs."""
        
        desc_label = ttk.Label(main_frame, text=desc_text, justify="center")
        desc_label.pack(pady=(0, 30))
        
        # Dataset info frame
        info_frame = ttk.LabelFrame(main_frame, text="Dataset Information", padding=15)
        info_frame.pack(fill="x", pady=(0, 20))
        
        info_text = """• Complete dataset with all available games
• Game metadata and player information
• Detailed move-by-move game logs
• ZIP format for easy extraction
• Updated regularly with new data"""
        
        info_label = ttk.Label(info_frame, text=info_text, justify="left")
        info_label.pack(anchor="w")
        
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
            text="File will be saved as: bga-tm-games_YYYYMMDD_HHMMSS.zip",
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
            text="ℹ️ Dataset Details",
            command=self.show_dataset_details
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
        self.log_message("Ready to download complete dataset from Google Drive")
    
    def browse_location(self):
        """Browse for download location"""
        folder = filedialog.askdirectory(
            title="Select download location",
            initialdir=self.location_var.get()
        )
        if folder:
            self.location_var.set(folder)
    
    def show_dataset_details(self):
        """Show detailed information about the dataset"""
        info_text = """BGA Terraforming Mars Complete Dataset

Content:
• All indexed games from BoardGameArena
• Complete game metadata (players, ELO, dates, etc.)
• Detailed move-by-move game logs
• Player statistics and performance data
• Corporation and card usage statistics

Format:
• ZIP archive containing JSON files
• Structured data ready for analysis
• Compatible with data analysis tools

File Size:
• Large file (several hundred MB to GB)
• Download time depends on internet speed
• Requires stable internet connection

Updates:
• Dataset is updated regularly
• Contains the most recent game data available
• Historical data preserved

Usage:
• Extract ZIP file after download
• Use JSON files for data analysis
• Compatible with Python, R, and other tools

Note: This download uses Google Drive and may show a virus scan warning for large files. This is normal and safe to proceed."""
        
        messagebox.showinfo("Dataset Details", info_text)
    
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
        
        # Confirm download
        if not messagebox.askyesno("Start Download", 
                                  "Download the complete BGA Terraforming Mars dataset?\n\n"
                                  "This is a large file and may take several minutes to download.\n"
                                  "You may see a virus scan warning from Google Drive - this is normal."):
            return
        
        # Initialize download
        self.is_downloading = True
        self.should_stop = False
        self.start_time = datetime.now()
        self.last_update_time = self.start_time
        self.last_downloaded_size = 0
        
        # Update UI
        self.download_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bga-tm-games_{timestamp}.zip"
        self.download_path = os.path.join(location, filename)
        
        # Reset progress tracking
        self.total_size = 0
        self.downloaded_size = 0
        self.download_speed = 0
        
        self.log_message("Starting download from Google Drive")
        self.log_message(f"File: {filename}")
        self.log_message("Connecting to Google Drive...")
        
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
        """Background worker for actual Google Drive download using subprocess to capture output"""
        try:
            self.frame.after(0, lambda: self.log_message("Starting gdown process..."))
            
            # Use subprocess to run gdown and capture its output
            cmd = [
                'python', '-m', 'gdown',
                self.file_url,
                '-O', self.download_path,
                '--fuzzy'
            ]
            
            # Start the subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Read output line by line and pipe to status log
            while True:
                if self.should_stop:
                    process.terminate()
                    break
                
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # Clean up the output line and add to log
                    line = output.strip()
                    if line:
                        # Add the gdown output directly to the status log
                        self.frame.after(0, lambda msg=line: self.log_message_raw(msg))
            
            # Wait for process to complete
            return_code = process.poll()
            
            if return_code == 0 and not self.should_stop:
                # Get final file size
                if os.path.exists(self.download_path):
                    self.total_size = os.path.getsize(self.download_path)
                    self.downloaded_size = self.total_size
                
                self.frame.after(0, lambda: self.log_message("✅ Download completed successfully!"))
                self.frame.after(0, self._download_completed)
            elif self.should_stop:
                self.frame.after(0, lambda: self.log_message("❌ Download cancelled"))
            else:
                self.frame.after(0, lambda: self.log_message("❌ Download failed"))
                
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower():
                error_msg = "Google Drive download quota exceeded. Please try again later."
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                error_msg = "Network connection error. Please check your internet connection."
            elif "permission" in error_msg.lower():
                error_msg = "Permission denied. Please check the download location."
            elif "not found" in error_msg.lower():
                error_msg = "gdown not found. Please install it with: pip install gdown"
            
            self.frame.after(0, lambda: self.log_message(f"❌ Download error: {error_msg}"))
        
        finally:
            # Clean up
            self.frame.after(0, self._download_finished)
    
    def _download_completed(self):
        """Handle successful download completion"""
        # Calculate final stats
        file_size_mb = self.total_size / (1024 * 1024) if self.total_size > 0 else 0
        
        message = f"Download completed successfully!\n\n"
        message += f"File saved to:\n{self.download_path}\n\n"
        message += f"Size: {file_size_mb:.1f} MB\n"
        
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            elapsed_str = str(elapsed).split('.')[0]
            message += f"Time: {elapsed_str}\n"
            
            if elapsed.total_seconds() > 0:
                avg_speed = file_size_mb / elapsed.total_seconds()
                message += f"Average speed: {avg_speed:.1f} MB/s"
        
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
                    self.log_message("Cleaned up partial download file")
                except Exception as e:
                    self.log_message(f"Could not clean up file: {str(e)}")
        else:
            self.progress_label.config(text="Download completed")
    
    def _update_progress_timer(self):
        """Update progress indicators"""
        if self.is_downloading:
            # Update progress label
            self.progress_label.config(text="Downloading...")
            
            # Schedule next update
            self.frame.after(1000, self._update_progress_timer)
        else:
            # Final update - progress is shown in the status log now
            pass
    
    def log_message(self, message):
        """Add a message to the status log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        self.log_text.config(state=tk.DISABLED)
    
    def log_message_raw(self, message):
        """Add a raw message to the status log without timestamp (for gdown output)"""
        log_entry = f"{message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        self.log_text.config(state=tk.DISABLED)
