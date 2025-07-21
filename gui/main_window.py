"""
Main Window for BGA TM Scraper GUI Application
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path

from gui.components.config_manager import ConfigManager
from gui.tabs.settings_tab import SettingsTab
from gui.tabs.scraping_tab import ScrapingTab
from gui.tabs.statistics_tab import StatisticsTab
from gui.tabs.download_tab import DownloadTab


class MainWindow:
    """Main application window with tabbed interface"""
    
    def __init__(self, root):
        self.root = root
        self.config_manager = ConfigManager()
        
        self.setup_window()
        self.create_menu()
        self.create_tabs()
        self.create_status_bar()
        
        # Load saved window state
        self.load_window_state()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_window(self):
        """Configure the main window"""
        self.root.title("BGA TM Scraper")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Configure the main grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Set window icon to our custom Mars icon
        try:
            # Try to load the Mars icon
            self.root.iconbitmap("assets/mars_icon.ico")
        except Exception as e:
            # Fallback if icon file is not found
            print(f"Could not load icon: {e}")
            try:
                # Try default system icon as fallback
                self.root.iconbitmap(default="")
            except:
                pass
    
    def create_menu(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import Config...", command=self.import_config)
        file_menu.add_command(label="Export Config...", command=self.export_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_tabs(self):
        """Create the main tabbed interface"""
        # Create notebook widget for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Create tab instances
        self.settings_tab = SettingsTab(self.notebook, self.config_manager)
        self.scraping_tab = ScrapingTab(self.notebook, self.config_manager)
        self.statistics_tab = StatisticsTab(self.notebook, self.config_manager)
        self.download_tab = DownloadTab(self.notebook, self.config_manager)
        
        # Add tabs to notebook
        self.notebook.add(self.settings_tab.frame, text="⚙️ Settings")
        self.notebook.add(self.scraping_tab.frame, text="🚀 Scraping")
        self.notebook.add(self.statistics_tab.frame, text="📊 Statistics")
        self.notebook.add(self.download_tab.frame, text="💾 Download Data")
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def create_status_bar(self):
        """Create the status bar at the bottom"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(
            self.status_frame, 
            text="Ready", 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def load_window_state(self):
        """Load saved window state from config"""
        ui_settings = self.config_manager.get_section("ui_settings")
        
        # Restore window size
        if "window_size" in ui_settings:
            width, height = ui_settings["window_size"]
            self.root.geometry(f"{width}x{height}")
        
        # Restore last selected tab
        if "last_tab" in ui_settings:
            try:
                self.notebook.select(ui_settings["last_tab"])
            except:
                pass  # Invalid tab index, ignore
    
    def save_window_state(self):
        """Save current window state to config"""
        # Get current window size
        geometry = self.root.geometry()
        width, height = geometry.split("+")[0].split("x")
        
        # Get current tab
        current_tab = self.notebook.index(self.notebook.select())
        
        # Update config
        ui_settings = {
            "window_size": [int(width), int(height)],
            "last_tab": current_tab
        }
        self.config_manager.update_section("ui_settings", ui_settings)
        self.config_manager.save_config()
    
    def on_tab_changed(self, event):
        """Handle tab change events"""
        selected_tab = self.notebook.select()
        tab_text = self.notebook.tab(selected_tab, "text")
        
        # Update status
        self.update_status(f"Switched to {tab_text}")
        
        # Refresh tab content if needed
        current_index = self.notebook.index(selected_tab)
        if current_index == 2:  # Statistics tab
            self.statistics_tab.refresh_data()
    
    def update_status(self, message):
        """Update the status bar message"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def import_config(self):
        """Import configuration from JSON file"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    # Import from JSON file
                    self.config_manager.import_config(file_path)
                    messagebox.showinfo("Import Success", f"Configuration imported from:\n{file_path}")
                    
                    # Reload settings in the settings tab
                    self.settings_tab.load_settings()
                    
                elif file_path.endswith('.py'):
                    # Import from Python config file (like config.py)
                    self._import_from_python_config(file_path)
                    
                else:
                    messagebox.showwarning("Import Warning", "Please select a JSON or Python config file.")
                    
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import config:\n{str(e)}")
    
    def _import_from_python_config(self, file_path):
        """Import configuration from Python config file (like config.py)"""
        import importlib.util
        
        try:
            # Load the Python module
            spec = importlib.util.spec_from_file_location("config", file_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # Extract relevant settings
            imported_settings = {}
            
            # BGA credentials
            if hasattr(config_module, 'BGA_EMAIL') and hasattr(config_module, 'BGA_PASSWORD'):
                imported_settings['bga_credentials'] = {
                    'email': config_module.BGA_EMAIL,
                    'password': config_module.BGA_PASSWORD
                }
            
            # Browser settings
            browser_settings = {}
            if hasattr(config_module, 'CHROME_PATH'):
                browser_settings['chrome_path'] = config_module.CHROME_PATH
            if hasattr(config_module, 'CHROMEDRIVER_PATH'):
                browser_settings['chromedriver_path'] = config_module.CHROMEDRIVER_PATH
            if hasattr(config_module, 'HEADLESS'):
                browser_settings['headless'] = config_module.HEADLESS
            if browser_settings:
                imported_settings['browser_settings'] = browser_settings
            
            # API settings
            api_settings = {}
            if hasattr(config_module, 'API_KEY'):
                api_settings['api_key'] = config_module.API_KEY
            if hasattr(config_module, 'API_BASE_URL'):
                api_settings['base_url'] = config_module.API_BASE_URL
            if api_settings:
                imported_settings['api_settings'] = api_settings
            
            # Scraping settings
            scraping_settings = {}
            if hasattr(config_module, 'REQUEST_DELAY'):
                scraping_settings['request_delay'] = config_module.REQUEST_DELAY
            if hasattr(config_module, 'MAX_RETRIES'):
                scraping_settings['max_retries'] = config_module.MAX_RETRIES
            if scraping_settings:
                imported_settings['scraping_settings'] = scraping_settings
            
            # Email settings
            email_settings = {}
            if hasattr(config_module, 'EMAIL_ENABLED'):
                email_settings['enabled'] = config_module.EMAIL_ENABLED
            if hasattr(config_module, 'SENDER_EMAIL'):
                email_settings['sender_email'] = config_module.SENDER_EMAIL
            if hasattr(config_module, 'APP_PASSWORD'):
                email_settings['app_password'] = config_module.APP_PASSWORD
            if hasattr(config_module, 'RECIPIENT_EMAIL'):
                email_settings['recipient_email'] = config_module.RECIPIENT_EMAIL
            if email_settings:
                imported_settings['email_settings'] = email_settings
            
            # Update config manager with imported settings
            for section, settings in imported_settings.items():
                if section == 'bga_credentials':
                    self.config_manager.set_bga_credentials(settings['email'], settings['password'])
                else:
                    self.config_manager.update_section(section, settings)
            
            # Save the updated config
            self.config_manager.save_config()
            
            # Reload settings in the settings tab
            self.settings_tab.load_settings()
            
            messagebox.showinfo("Import Success", 
                               f"Configuration imported from Python file:\n{file_path}\n\n"
                               f"Imported {len(imported_settings)} sections.")
            
        except Exception as e:
            messagebox.showerror("Import Error", 
                               f"Failed to import from Python config:\n{str(e)}\n\n"
                               "Make sure the file is a valid Python config file.")
    
    def export_config(self):
        """Export current configuration"""
        from tkinter import filedialog
        
        file_path = filedialog.asksaveasfilename(
            title="Export configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.config_manager.export_config(file_path)
                messagebox.showinfo("Export Success", f"Configuration exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export config:\n{str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """BGA TM Scraper v1.0

A desktop GUI application for scraping and managing 
Terraforming Mars game data from BoardGameArena.

Features:
• Automated game data collection
• Progress tracking and statistics
• Data download and management
• User-friendly interface

Built with Python and Tkinter"""
        
        messagebox.showinfo("About BGA TM Scraper", about_text)
    
    def on_closing(self):
        """Handle application closing"""
        # Save window state
        self.save_window_state()
        
        # Check if any operations are running
        if hasattr(self.scraping_tab, 'is_scraping') and self.scraping_tab.is_scraping:
            if messagebox.askokcancel("Quit", "Scraping is in progress. Do you want to quit?"):
                self.scraping_tab.stop_scraping()
                self.root.destroy()
        else:
            self.root.destroy()
