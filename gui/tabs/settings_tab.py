"""
Settings Tab for BGA TM Scraper GUI
Handles all configuration settings with validation and user-friendly interface
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os
import threading
import requests
import sys
import platform
from datetime import datetime

# Add the parent directory to the path to import bga_tm_scraper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bga_tm_scraper.bga_session import BGASession


class SettingsTab:
    """Settings configuration tab with form validation"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Variables for form fields
        self.setup_variables()
        
        # Create the UI
        self.create_widgets()
        
        # Load current settings
        self.load_settings()
        
        # Setup validation
        self.setup_validation()
    
    def setup_variables(self):
        """Initialize tkinter variables for form fields"""
        # BGA Credentials
        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()
        
        # Browser Settings
        self.chrome_path_var = tk.StringVar()
        self.chromedriver_path_var = tk.StringVar()
        self.headless_var = tk.BooleanVar()
        
        # API Settings
        self.api_key_var = tk.StringVar()
        self.api_url_var = tk.StringVar()
        self.api_timeout_var = tk.IntVar()
        
        # Scraping Settings
        self.request_delay_var = tk.DoubleVar()
        self.max_retries_var = tk.IntVar()
        self.speed_profile_var = tk.StringVar()
        
        # Email Settings
        self.email_enabled_var = tk.BooleanVar()
        self.sender_email_var = tk.StringVar()
        self.app_password_var = tk.StringVar()
        self.recipient_email_var = tk.StringVar()
        self.notify_completion_var = tk.BooleanVar()
        self.notify_error_var = tk.BooleanVar()
        self.notify_limit_var = tk.BooleanVar()
        
        # Validation indicators
        self.email_valid = tk.BooleanVar()
        self.password_valid = tk.BooleanVar()
        self.api_key_valid = tk.BooleanVar()
        self.chrome_path_valid = tk.BooleanVar()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Create main vertical layout
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill="both", expand=True)
        
        # Top area for scrollable settings
        settings_area = ttk.Frame(main_container)
        settings_area.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        
        # Create scrollable frame for settings with better visual styling
        canvas = tk.Canvas(settings_area, highlightthickness=1, highlightbackground="lightgray")
        scrollbar = ttk.Scrollbar(settings_area, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollable components
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create sections in scrollable area
        self.create_bga_section(scrollable_frame)
        self.create_browser_section(scrollable_frame)
        self.create_api_section(scrollable_frame)
        self.create_scraping_section(scrollable_frame)
        
        # Add a visual separator
        separator = ttk.Separator(main_container, orient="horizontal")
        separator.pack(fill="x", padx=10, pady=5)
        
        # Bottom area for fixed buttons
        button_area = ttk.Frame(main_container)
        button_area.pack(fill="x", padx=10, pady=(5, 10))
        
        # Create buttons in bottom area
        self.create_buttons_section(button_area)
        
        # Enhanced mouse wheel scrolling
        self.canvas = canvas  # Store reference for later use
        self.setup_mouse_wheel_scrolling(canvas, scrollable_frame)
    
    def create_bga_section(self, parent):
        """Create BGA credentials section"""
        section_frame = ttk.LabelFrame(parent, text="BoardGameArena Account", padding=10)
        section_frame.pack(fill="x", padx=10, pady=5)
        
        # Email field
        ttk.Label(section_frame, text="Email:").pack(anchor="w", pady=(0, 2))
        email_entry = ttk.Entry(section_frame, textvariable=self.email_var, width=50)
        email_entry.pack(fill="x", pady=(0, 5))
        
        # Password field
        ttk.Label(section_frame, text="Password:").pack(anchor="w", pady=(0, 2))
        password_entry_frame = ttk.Frame(section_frame)
        password_entry_frame.pack(fill="x", pady=(0, 5))
        
        self.password_entry = ttk.Entry(password_entry_frame, textvariable=self.password_var, 
                                       show="*", width=45)
        self.password_entry.pack(side="left", fill="x", expand=True)
        
        self.show_password_var = tk.BooleanVar()
        show_password_cb = ttk.Checkbutton(password_entry_frame, text="Show", 
                                          variable=self.show_password_var,
                                          command=self.toggle_password_visibility)
        show_password_cb.pack(side="right", padx=(5, 0))
        
        # BGA connection status
        self.bga_status_label = ttk.Label(section_frame, text="", foreground="green")
        self.bga_status_label.pack(anchor="w", pady=2)
        
        # Test connection button
        test_btn = ttk.Button(section_frame, text="Test Connection", 
                             command=self.test_bga_connection)
        test_btn.pack(pady=5)
    
    def create_browser_section(self, parent):
        """Create browser settings section"""
        section_frame = ttk.LabelFrame(parent, text="Browser Settings", padding=10)
        section_frame.pack(fill="x", padx=10, pady=5)
        
        # Chrome path
        ttk.Label(section_frame, text="Chrome Path:").pack(anchor="w", pady=(0, 2))
        chrome_path_frame = ttk.Frame(section_frame)
        chrome_path_frame.pack(fill="x", pady=(0, 5))
        
        chrome_entry = ttk.Entry(chrome_path_frame, textvariable=self.chrome_path_var)
        chrome_entry.pack(side="left", fill="x", expand=True)
        
        chrome_browse_btn = ttk.Button(chrome_path_frame, text="Browse...", 
                                      command=self.browse_chrome_path)
        chrome_browse_btn.pack(side="right", padx=(5, 0))
        
        # ChromeDriver path
        driver_frame = ttk.Frame(section_frame)
        driver_frame.pack(fill="x", pady=2)
        
        ttk.Label(driver_frame, text="ChromeDriver Path (optional):").pack(side="left", anchor="w")
        
        driver_path_frame = ttk.Frame(section_frame)
        driver_path_frame.pack(fill="x", pady=(0, 5))
        
        driver_entry = ttk.Entry(driver_path_frame, textvariable=self.chromedriver_path_var)
        driver_entry.pack(side="left", fill="x", expand=True)
        
        driver_browse_btn = ttk.Button(driver_path_frame, text="Browse...", 
                                      command=self.browse_chromedriver_path)
        driver_browse_btn.pack(side="right", padx=(5, 0))
        
        # Headless mode
        headless_cb = ttk.Checkbutton(section_frame, text="Run browser in headless mode (recommended)", 
                                     variable=self.headless_var)
        headless_cb.pack(anchor="w", pady=2)
        
        # Chrome status label
        self.chrome_status_label = ttk.Label(section_frame, text="", foreground="blue")
        self.chrome_status_label.pack(anchor="w", pady=2)
        
        # Info label
        info_label = ttk.Label(section_frame, 
                              text="Note: ChromeDriver will be downloaded automatically if not specified",
                              foreground="gray")
        info_label.pack(anchor="w", pady=2)
    
    def create_api_section(self, parent):
        """Create API settings section"""
        section_frame = ttk.LabelFrame(parent, text="API Configuration", padding=10)
        section_frame.pack(fill="x", padx=10, pady=5)
        
        # API Key
        ttk.Label(section_frame, text="API Key:").pack(anchor="w", pady=(0, 2))
        api_key_entry = ttk.Entry(section_frame, textvariable=self.api_key_var, width=50, show="*")
        api_key_entry.pack(fill="x", pady=(0, 5))
        
        # API URL
        ttk.Label(section_frame, text="API Base URL:").pack(anchor="w", pady=(5, 2))
        api_url_entry = ttk.Entry(section_frame, textvariable=self.api_url_var, width=50)
        api_url_entry.pack(fill="x", pady=(0, 5))
        
        # Timeout
        timeout_frame = ttk.Frame(section_frame)
        timeout_frame.pack(fill="x", pady=2)
        
        ttk.Label(timeout_frame, text="Timeout (seconds):").pack(side="left", anchor="w")
        timeout_spin = ttk.Spinbox(timeout_frame, from_=10, to=120, textvariable=self.api_timeout_var, width=10)
        timeout_spin.pack(side="right")
        
        # API connection status
        self.api_status_label = ttk.Label(section_frame, text="", foreground="green")
        self.api_status_label.pack(anchor="w", pady=2)
        
        # Test API button
        test_api_btn = ttk.Button(section_frame, text="Test API Connection", 
                                 command=self.test_api_connection)
        test_api_btn.pack(pady=5)
    
    def create_scraping_section(self, parent):
        """Create scraping settings section"""
        section_frame = ttk.LabelFrame(parent, text="Scraping Settings", padding=10)
        section_frame.pack(fill="x", padx=10, pady=5)
        
        # Request delay
        delay_frame = ttk.Frame(section_frame)
        delay_frame.pack(fill="x", pady=2)
        
        ttk.Label(delay_frame, text="Request Delay (seconds):").pack(side="left", anchor="w")
        delay_spin = ttk.Spinbox(delay_frame, from_=0.1, to=10.0, increment=0.1, 
                                textvariable=self.request_delay_var, width=10)
        delay_spin.pack(side="right")
        
        # Max retries
        retries_frame = ttk.Frame(section_frame)
        retries_frame.pack(fill="x", pady=2)
        
        ttk.Label(retries_frame, text="Max Retries:").pack(side="left", anchor="w")
        retries_spin = ttk.Spinbox(retries_frame, from_=1, to=10, 
                                  textvariable=self.max_retries_var, width=10)
        retries_spin.pack(side="right")
        
        # Speed profile
        speed_frame = ttk.Frame(section_frame)
        speed_frame.pack(fill="x", pady=2)
        
        ttk.Label(speed_frame, text="Speed Profile:").pack(side="left", anchor="w")
        speed_combo = ttk.Combobox(speed_frame, textvariable=self.speed_profile_var, 
                                  values=["FAST", "NORMAL", "SLOW"], state="readonly", width=15)
        speed_combo.pack(side="right")
    
    def create_buttons_section(self, parent):
        """Create action buttons section"""
        # Create a horizontal button layout for bottom panel
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=10)
        
        # Left side - main action buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side="left", fill="x", expand=True)
        
        # Save button - make it VERY prominent
        save_btn = ttk.Button(left_buttons, text="💾 SAVE SETTINGS", 
                             command=self.save_settings, style="Accent.TButton")
        save_btn.pack(side="left", padx=(0, 10), ipady=8, ipadx=20)
        
        # Reset button
        reset_btn = ttk.Button(left_buttons, text="🔄 Reset to Defaults", 
                              command=self.reset_settings)
        reset_btn.pack(side="left", padx=(0, 10), ipady=5)
        
        # Validate button
        validate_btn = ttk.Button(left_buttons, text="✅ Validate Settings", 
                                 command=self.validate_settings)
        validate_btn.pack(side="left", ipady=5)
        
        # Right side - status and info
        right_info = ttk.Frame(button_frame)
        right_info.pack(side="right")
        
        # Status label
        self.status_label = ttk.Label(right_info, text="", foreground="green", 
                                     font=("TkDefaultFont", 10, "bold"))
        self.status_label.pack(anchor="e")
        
        # Add a helpful note below buttons
        note_frame = ttk.Frame(parent)
        note_frame.pack(fill="x", pady=(0, 5))
        
        note_label = ttk.Label(note_frame, 
                              text="💡 Remember to save your settings after making changes!",
                              foreground="blue", font=("TkDefaultFont", 9, "italic"))
        note_label.pack()
    
    def setup_mouse_wheel_scrolling(self, canvas, scrollable_frame):
        """Setup enhanced mouse wheel scrolling for all widgets"""
        def _on_mousewheel(event):
            # Scroll the canvas
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(widget):
            """Recursively bind mouse wheel events to widget and all its children"""
            # Bind to the widget itself
            widget.bind("<MouseWheel>", _on_mousewheel)
            
            # Recursively bind to all children
            for child in widget.winfo_children():
                _bind_to_mousewheel(child)
        
        # Bind to canvas
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Bind to scrollable frame and all its children
        _bind_to_mousewheel(scrollable_frame)
        
        # Also bind to the main settings area to catch any missed widgets
        canvas.bind("<Enter>", lambda e: canvas.focus_set())
    
    def detect_chrome_path(self):
        """Auto-detect Chrome installation path across platforms"""
        system = platform.system()
        chrome_paths = []
        
        if system == "Windows":
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            ]
        elif system == "Darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
        elif system == "Linux":
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
            ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def setup_validation(self):
        """Setup real-time validation for form fields"""
        # Bind validation to key events
        self.email_var.trace_add("write", self.validate_email)
        self.password_var.trace_add("write", self.validate_password)
        self.api_key_var.trace_add("write", self.validate_api_key)
        self.chrome_path_var.trace_add("write", self.validate_chrome_path)
    
    def load_settings(self):
        """Load current settings from config manager"""
        # BGA Credentials
        email, password = self.config_manager.get_bga_credentials()
        self.email_var.set(email)
        self.password_var.set(password)
        
        # Browser Settings with Chrome auto-detection
        browser_settings = self.config_manager.get_section("browser_settings")
        saved_chrome_path = browser_settings.get("chrome_path", "")
        
        if saved_chrome_path:
            # Use saved path, no auto-detection needed
            self.chrome_path_var.set(saved_chrome_path)
            self.show_chrome_status("Using saved Chrome path")
        else:
            # No saved path, try auto-detection
            detected_path = self.detect_chrome_path()
            if detected_path:
                self.chrome_path_var.set(detected_path)
                self.show_chrome_status("✅ Chrome found automatically. Save settings to remember this path.")
            else:
                self.chrome_path_var.set("")
                self.show_chrome_status("⚠️ Chrome not found. Please browse for chrome.exe or install Chrome.")
        
        self.chromedriver_path_var.set(browser_settings.get("chromedriver_path", ""))
        self.headless_var.set(browser_settings.get("headless", True))
        
        # API Settings with default key handling
        api_settings = self.config_manager.get_section("api_settings")
        api_key = api_settings.get("api_key", "")
        
        self.api_key_var.set(api_key)
        self.api_url_var.set(api_settings.get("base_url", ""))
        self.api_timeout_var.set(api_settings.get("timeout", 30))
        
        # Scraping Settings
        scraping_settings = self.config_manager.get_section("scraping_settings")
        self.request_delay_var.set(scraping_settings.get("request_delay", 1.0))
        self.max_retries_var.set(scraping_settings.get("max_retries", 3))
        self.speed_profile_var.set(scraping_settings.get("speed_profile", "FAST"))
    
    def save_settings(self):
        """Save current settings to config manager"""
        try:
            # BGA Credentials
            self.config_manager.set_bga_credentials(
                self.email_var.get(),
                self.password_var.get()
            )
            
            # Browser Settings
            self.config_manager.update_section("browser_settings", {
                "chrome_path": self.chrome_path_var.get(),
                "chromedriver_path": self.chromedriver_path_var.get(),
                "headless": self.headless_var.get()
            })
            
            # API Settings
            self.config_manager.update_section("api_settings", {
                "api_key": self.api_key_var.get(),
                "base_url": self.api_url_var.get(),
                "timeout": self.api_timeout_var.get()
            })
            
            # Scraping Settings
            self.config_manager.update_section("scraping_settings", {
                "request_delay": self.request_delay_var.get(),
                "max_retries": self.max_retries_var.get(),
                "speed_profile": self.speed_profile_var.get()
            })
            
            # Email Settings
            self.config_manager.update_section("email_settings", {
                "enabled": self.email_enabled_var.get(),
                "sender_email": self.sender_email_var.get(),
                "app_password": self.app_password_var.get(),
                "recipient_email": self.recipient_email_var.get(),
                "notify_on_completion": self.notify_completion_var.get(),
                "notify_on_error": self.notify_error_var.get(),
                "notify_on_daily_limit": self.notify_limit_var.get()
            })
            
            # Save to file
            self.config_manager.save_config()
            
            self.status_label.config(text="Settings saved successfully!", foreground="green")
            self.frame.after(3000, lambda: self.status_label.config(text=""))
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings:\n{str(e)}")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            self.config_manager.config_data = self.config_manager.get_default_config()
            self.load_settings()
            self.status_label.config(text="Settings reset to defaults", foreground="orange")
            self.frame.after(3000, lambda: self.status_label.config(text=""))
    
    def validate_settings(self):
        """Validate current form data and show results"""
        issues = {
            "errors": [],
            "warnings": []
        }
        
        # Validate BGA credentials (current form values)
        email = self.email_var.get()
        password = self.password_var.get()
        
        if not email or "@" not in email or "." not in email or len(email) <= 5:
            issues["errors"].append("Valid BGA email is required")
        
        if not password or len(password) == 0:
            issues["errors"].append("BGA password is required")
        
        # Validate Chrome path (current form value)
        chrome_path = self.chrome_path_var.get()
        if not chrome_path:
            issues["errors"].append("Chrome path is required")
        elif not Path(chrome_path).exists():
            issues["errors"].append("Chrome path does not exist")
        
        # Validate API key (current form value)
        api_key = self.api_key_var.get()
        if not api_key or api_key == "your_api_key_here":
            issues["warnings"].append("API key not configured")
        elif len(api_key) <= 10:
            issues["warnings"].append("API key seems too short")
        
        # Validate API URL (current form value)
        api_url = self.api_url_var.get()
        if not api_url:
            issues["warnings"].append("API base URL not configured")
        
        # Show results
        if not issues["errors"] and not issues["warnings"]:
            messagebox.showinfo("Validation", "✅ All current settings are valid!")
        else:
            message = "Validation Results for Current Form Data:\n\n"
            
            if issues["errors"]:
                message += "❌ Errors (must be fixed):\n"
                for error in issues["errors"]:
                    message += f"• {error}\n"
                message += "\n"
            
            if issues["warnings"]:
                message += "⚠️ Warnings (recommended to fix):\n"
                for warning in issues["warnings"]:
                    message += f"• {warning}\n"
            
            if issues["errors"]:
                messagebox.showerror("Validation Issues", message)
            else:
                messagebox.showwarning("Validation Warnings", message)
    
    # Validation methods (simplified - no more visual indicators)
    def validate_email(self, *args):
        """Validate email field"""
        email = self.email_var.get()
        is_valid = "@" in email and "." in email and len(email) > 5
        self.email_valid.set(is_valid)
    
    def validate_password(self, *args):
        """Validate password field"""
        password = self.password_var.get()
        is_valid = len(password) > 0
        self.password_valid.set(is_valid)
    
    def validate_api_key(self, *args):
        """Validate API key field"""
        api_key = self.api_key_var.get()
        is_valid = len(api_key) > 10 and api_key != "your_api_key_here"
        self.api_key_valid.set(is_valid)
    
    def validate_chrome_path(self, *args):
        """Validate Chrome path field"""
        chrome_path = self.chrome_path_var.get()
        if not chrome_path:
            self.chrome_path_valid.set(False)
        else:
            is_valid = Path(chrome_path).exists()
            self.chrome_path_valid.set(is_valid)
    
    def show_chrome_status(self, message):
        """Display Chrome detection status message"""
        self.chrome_status_label.config(text=message)
    
    def show_api_status(self, message):
        """Display API key status message"""
        self.api_status_label.config(text=message)
    
    # UI event handlers
    def toggle_password_visibility(self):
        """Toggle password field visibility"""
        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")
    
    def toggle_email_settings(self):
        """Enable/disable email settings based on checkbox"""
        state = "normal" if self.email_enabled_var.get() else "disabled"
        
        for widget in self.email_settings_frame.winfo_children():
            if isinstance(widget, (ttk.Entry, ttk.Checkbutton)):
                widget.config(state=state)
    
    def browse_chrome_path(self):
        """Browse for Chrome executable"""
        file_path = filedialog.askopenfilename(
            title="Select Chrome executable",
            filetypes=[
                ("Executable files", "*.exe"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.chrome_path_var.set(file_path)
    
    def browse_chromedriver_path(self):
        """Browse for ChromeDriver executable"""
        file_path = filedialog.askopenfilename(
            title="Select ChromeDriver executable",
            filetypes=[
                ("Executable files", "*.exe"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.chromedriver_path_var.set(file_path)
    
    def test_bga_connection(self):
        """Test BGA connection using real BGASession"""
        email = self.email_var.get()
        password = self.password_var.get()
        
        if not email or not password:
            messagebox.showwarning("Test Connection", "Please enter both email and password")
            return
        
        # Get browser settings
        chrome_path = self.chrome_path_var.get() or None
        chromedriver_path = self.chromedriver_path_var.get() or None
        headless = self.headless_var.get()
        
        # Show progress dialog
        progress_dialog = self._create_progress_dialog("Testing BGA Connection", 
                                                      "Connecting to BoardGameArena...")
        
        # Start test in background thread
        def test_worker():
            try:
                # Create BGASession instance
                session = BGASession(
                    email=email,
                    password=password,
                    chromedriver_path=chromedriver_path,
                    chrome_path=chrome_path,
                    headless=headless
                )
                
                # Update progress
                self.frame.after(0, lambda: self._update_progress_dialog(progress_dialog, 
                                                                        "Authenticating with BGA..."))
                
                # Attempt login
                success = session.login()
                
                if success:
                    # Test a simple authenticated request
                    self.frame.after(0, lambda: self._update_progress_dialog(progress_dialog, 
                                                                            "Verifying authentication..."))
                    
                    # Check authentication status
                    auth_status = session.check_authentication_status()
                    
                    # Close session
                    session.close_browser()
                    
                    # Show success message
                    self.frame.after(0, lambda: self._show_bga_test_result(progress_dialog, True, 
                                                                          auth_status))
                else:
                    session.close_browser()
                    self.frame.after(0, lambda: self._show_bga_test_result(progress_dialog, False, 
                                                                          "Authentication failed"))
                    
            except Exception as e:
                # Show error message
                self.frame.after(0, lambda: self._show_bga_test_result(progress_dialog, False, str(e)))
        
        # Start test thread
        test_thread = threading.Thread(target=test_worker, daemon=True)
        test_thread.start()
    
    def test_api_connection(self):
        """Test API connection using HelloWorldFunction endpoint"""
        api_key = self.api_key_var.get()
        api_url = self.api_url_var.get()
        
        if not api_key:
            messagebox.showwarning("Test API", "Please enter an API key")
            return
        
        if not api_url:
            messagebox.showwarning("Test API", "Please enter an API base URL")
            return
        
        # Show progress dialog
        progress_dialog = self._create_progress_dialog("Testing API Connection", 
                                                      "Connecting to API...")
        
        # Start test in background thread
        def test_worker():
            try:
                # Construct HelloWorldFunction URL
                test_url = f"{api_url.rstrip('/')}/HelloWorldFunction"
                
                # Update progress
                self.frame.after(0, lambda: self._update_progress_dialog(progress_dialog, 
                                                                        "Calling HelloWorldFunction..."))
                
                # Make API request
                timeout = self.api_timeout_var.get()
                response = requests.get(
                    test_url,
                    params={"code": api_key},
                    timeout=timeout
                )
                
                # Check response
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        self.frame.after(0, lambda: self._show_api_test_result(progress_dialog, True, 
                                                                              response_data))
                    except:
                        # Not JSON, but still successful
                        self.frame.after(0, lambda: self._show_api_test_result(progress_dialog, True, 
                                                                              response.text))
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    self.frame.after(0, lambda: self._show_api_test_result(progress_dialog, False, 
                                                                          error_msg))
                    
            except requests.exceptions.Timeout:
                self.frame.after(0, lambda: self._show_api_test_result(progress_dialog, False, 
                                                                      "Request timed out"))
            except requests.exceptions.ConnectionError:
                self.frame.after(0, lambda: self._show_api_test_result(progress_dialog, False, 
                                                                      "Connection error - check URL"))
            except Exception as e:
                self.frame.after(0, lambda: self._show_api_test_result(progress_dialog, False, str(e)))
        
        # Start test thread
        test_thread = threading.Thread(target=test_worker, daemon=True)
        test_thread.start()
    
    def _create_progress_dialog(self, title, message):
        """Create a progress dialog window"""
        dialog = tk.Toplevel(self.frame)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (150 // 2)
        dialog.geometry(f"400x150+{x}+{y}")
        
        # Create content
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Message label
        message_label = ttk.Label(main_frame, text=message, font=("TkDefaultFont", 10))
        message_label.pack(pady=(0, 15))
        
        # Progress bar
        progress_bar = ttk.Progressbar(main_frame, mode="indeterminate")
        progress_bar.pack(fill="x", pady=(0, 15))
        progress_bar.start()
        
        # Cancel button
        cancel_btn = ttk.Button(main_frame, text="Cancel", 
                               command=lambda: dialog.destroy())
        cancel_btn.pack()
        
        # Store references
        dialog.message_label = message_label
        dialog.progress_bar = progress_bar
        
        return dialog
    
    def _update_progress_dialog(self, dialog, message):
        """Update progress dialog message"""
        if dialog and dialog.winfo_exists():
            dialog.message_label.config(text=message)
    
    def _show_bga_test_result(self, progress_dialog, success, result):
        """Show BGA test result and close progress dialog"""
        if progress_dialog and progress_dialog.winfo_exists():
            progress_dialog.destroy()
        
        if success:
            auth_status = result
            # Show green success text
            self.bga_status_label.config(text="✅ BGA connection verified", foreground="green")
            
            # Also show detailed dialog
            message = "✅ BGA Connection Successful!\n\n"
            message += f"Session authenticated: {auth_status.get('session_authenticated', False)}\n"
            message += f"Browser authenticated: {auth_status.get('browser_authenticated', False)}\n"
            message += f"Fully authenticated: {auth_status.get('fully_authenticated', False)}\n\n"
            message += "Your BGA credentials are working correctly."
            
            messagebox.showinfo("BGA Connection Test", message)
        else:
            # Clear any previous success message
            self.bga_status_label.config(text="", foreground="green")
            
            error_msg = str(result)
            message = "❌ BGA Connection Failed\n\n"
            message += f"Error: {error_msg}\n\n"
            message += "Please check your credentials and browser settings."
            
            messagebox.showerror("BGA Connection Test", message)
    
    def _show_api_test_result(self, progress_dialog, success, result):
        """Show API test result and close progress dialog"""
        if progress_dialog and progress_dialog.winfo_exists():
            progress_dialog.destroy()
        
        if success:
            # Show green success text
            self.api_status_label.config(text="✅ API connection verified", foreground="green")
            
            # Also show detailed dialog
            message = "✅ API Connection Successful!\n\n"
            message += f"HelloWorldFunction response:\n{str(result)}\n\n"
            message += "Your API key and endpoint are working correctly."
            
            messagebox.showinfo("API Connection Test", message)
        else:
            # Clear any previous success message
            self.api_status_label.config(text="", foreground="green")
            
            error_msg = str(result)
            message = "❌ API Connection Failed\n\n"
            message += f"Error: {error_msg}\n\n"
            message += "Please check your API key and base URL."
            
            messagebox.showerror("API Connection Test", message)
