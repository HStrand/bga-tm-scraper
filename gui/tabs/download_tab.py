"""
Download Tab for BGA TM Scraper GUI
Handles downloading the complete dataset from the API
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from datetime import datetime, timedelta


class DownloadTab:
    """Download tab for retrieving the complete dataset from the API"""
    
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
        desc_text = """Download the complete BGA Terraforming Mars dataset."""
        
        desc_label = ttk.Label(main_frame, text=desc_text, justify="center")
        desc_label.pack(pady=(0, 30))
        
        # Dataset info frame
        info_frame = ttk.LabelFrame(main_frame, text="Dataset Information", padding=15)
        info_frame.pack(fill="x", pady=(0, 20))
        
        info_text = """• A single ZIP file with all games
• One JSON file per game
• Detailed move-by-move game logs
• NB: The ZIP archive is generated periodically to reduce server costs and might not contain all the latest games
"""
        
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
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Download Progress", padding=15)
        progress_frame.pack(fill="both", expand=True)
        
        # Progress bar
        progress_bar_frame = ttk.Frame(progress_frame)
        progress_bar_frame.pack(fill="x", pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(
            progress_bar_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill="x", pady=(0, 5))
        
        # Progress info
        progress_info_frame = ttk.Frame(progress_frame)
        progress_info_frame.pack(fill="x", pady=(0, 10))
        
        self.progress_label = ttk.Label(progress_info_frame, text="Ready to download")
        self.progress_label.pack(side="left")
        
        # Progress details (size, speed, ETA)
        self.progress_details_label = ttk.Label(
            progress_frame,
            text="",
            font=("TkDefaultFont", 9),
            foreground="gray"
        )
        self.progress_details_label.pack(anchor="w", pady=(0, 10))
        
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
        self.log_message("Ready to download complete dataset from API")
    
    def browse_location(self):
        """Browse for download location"""
        folder = filedialog.askdirectory(
            title="Select download location",
            initialdir=self.location_var.get()
        )
        if folder:
            self.location_var.set(folder)
    
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
                                  "This is a large file and may take several minutes to download."):
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
        
        self.log_message("Starting download from API")
        self.log_message(f"File: {filename}")
        self.log_message("Connecting to API...")
        
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
    
    def _progress_callback(self, downloaded_bytes, total_bytes):
        """Progress callback function called by the API client"""
        if self.should_stop:
            return
        
        # Update progress data
        self.downloaded_size = downloaded_bytes
        if total_bytes:
            self.total_size = total_bytes
        
        # Calculate speed and ETA
        current_time = datetime.now()
        if self.last_update_time and (current_time - self.last_update_time).total_seconds() >= 0.5:
            # Update speed calculation every 0.5 seconds
            time_diff = (current_time - self.last_update_time).total_seconds()
            bytes_diff = downloaded_bytes - self.last_downloaded_size
            
            if time_diff > 0:
                self.download_speed = bytes_diff / time_diff
            
            self.last_update_time = current_time
            self.last_downloaded_size = downloaded_bytes
        elif self.last_update_time is None:
            self.last_update_time = current_time
            self.last_downloaded_size = downloaded_bytes
        
        # Schedule UI update on main thread
        self.frame.after(0, self._update_progress_ui)
    
    def _update_progress_ui(self):
        """Update the progress UI elements (called on main thread)"""
        if not self.is_downloading:
            return
        
        # Update progress bar
        if self.total_size and self.total_size > 0:
            progress_percent = (self.downloaded_size / self.total_size) * 100
            self.progress_bar['value'] = progress_percent
            self.progress_bar['mode'] = 'determinate'
        else:
            # Indeterminate mode if we don't know total size
            self.progress_bar['mode'] = 'indeterminate'
            if not hasattr(self, '_indeterminate_started'):
                self.progress_bar.start(10)
                self._indeterminate_started = True
        
        # Update progress label
        if self.total_size and self.total_size > 0:
            downloaded_mb = self.downloaded_size / (1024 * 1024)
            total_mb = self.total_size / (1024 * 1024)
            progress_percent = (self.downloaded_size / self.total_size) * 100
            self.progress_label.config(text=f"Downloading... {progress_percent:.1f}%")
            
            # Update details label
            details = f"Downloaded {downloaded_mb:.1f} MB / {total_mb:.1f} MB"
            
            if self.download_speed > 0:
                speed_mb = self.download_speed / (1024 * 1024)
                details += f" - Speed: {speed_mb:.1f} MB/s"
                
                # Calculate ETA
                remaining_bytes = self.total_size - self.downloaded_size
                if remaining_bytes > 0:
                    eta_seconds = remaining_bytes / self.download_speed
                    if eta_seconds < 60:
                        eta_str = f"{int(eta_seconds)}s"
                    elif eta_seconds < 3600:
                        eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                    else:
                        hours = int(eta_seconds // 3600)
                        minutes = int((eta_seconds % 3600) // 60)
                        eta_str = f"{hours}h {minutes}m"
                    details += f" - ETA: {eta_str}"
            
            self.progress_details_label.config(text=details)
        else:
            self.progress_label.config(text="Downloading...")
            downloaded_mb = self.downloaded_size / (1024 * 1024)
            self.progress_details_label.config(text=f"Downloaded {downloaded_mb:.1f} MB")
    
    def _download_worker(self):
        """Background worker for API download"""
        try:
            from gui.api_client import APIClient
            
            self.frame.after(0, lambda: self.log_message("Getting file information..."))
            
            # Get API key from config
            api_key = self.config_manager.get_value("api_settings", "api_key", "")
            
            if not api_key:
                self.frame.after(0, lambda: self.log_message("❌ API key not configured. Please set it in Settings."))
                return
            
            # Create API client
            from gui.api_client import APIClient
            api_client = APIClient(api_key)
            
            # Check if download should be cancelled before starting
            if self.should_stop:
                self.frame.after(0, lambda: self.log_message("❌ Download cancelled"))
                return
            
            # First, get file information
            file_info = api_client.get_latest_zip_info()
            if file_info and file_info.get('success'):
                # Set the total size from the API response
                self.total_size = file_info.get('sizeInBytes', 0)
                file_name = file_info.get('fileName', 'unknown')
                size_formatted = file_info.get('sizeFormatted', 'unknown size')
                
                self.frame.after(0, lambda: self.log_message(f"File: {file_name} ({size_formatted})"))
                self.frame.after(0, lambda: self.log_message("Starting download..."))
            else:
                self.frame.after(0, lambda: self.log_message("⚠️ Could not get file info, proceeding with download..."))
            
            # Check again if download should be cancelled
            if self.should_stop:
                self.frame.after(0, lambda: self.log_message("❌ Download cancelled"))
                return
            
            # Perform the download with progress callback and known file size
            success = api_client.download_latest_zip(
                self.download_path, 
                self._progress_callback, 
                self.total_size if self.total_size > 0 else None
            )
            
            if success and not self.should_stop:
                # Get final file size if not already set
                if os.path.exists(self.download_path) and self.total_size == 0:
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
            if "timeout" in error_msg.lower():
                error_msg = "Download timeout. The file may be very large. Please try again."
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                error_msg = "Network connection error. Please check your internet connection."
            elif "permission" in error_msg.lower():
                error_msg = "Permission denied. Please check the download location."
            elif "404" in error_msg or "not found" in error_msg.lower():
                error_msg = "File not found on server. Please try again later."
            
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
        
        # Stop indeterminate progress bar if it was started
        if hasattr(self, '_indeterminate_started'):
            self.progress_bar.stop()
            delattr(self, '_indeterminate_started')
        
        # Update UI
        self.download_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        
        if self.should_stop:
            self.progress_label.config(text="Download cancelled")
            self.progress_details_label.config(text="")
            self.progress_bar['value'] = 0
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
            # Keep progress bar at 100% and details showing final stats
            if self.total_size > 0:
                self.progress_bar['value'] = 100
                downloaded_mb = self.total_size / (1024 * 1024)
                if self.start_time:
                    elapsed = datetime.now() - self.start_time
                    if elapsed.total_seconds() > 0:
                        avg_speed = downloaded_mb / elapsed.total_seconds()
                        self.progress_details_label.config(
                            text=f"Downloaded {downloaded_mb:.1f} MB - Average speed: {avg_speed:.1f} MB/s"
                        )
    
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
