"""
Statistics Tab for BGA TM Scraper GUI
Simple placeholder indicating the feature is coming soon
"""

import tkinter as tk
from tkinter import ttk


class StatisticsTab:
    """Statistics tab placeholder for future implementation"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Create the UI
        self.create_widgets()
    
    def create_widgets(self):
        """Create the coming soon UI"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        # Center everything
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=0, column=0)
        
        # Large icon
        icon_label = ttk.Label(
            content_frame, 
            text="📊", 
            font=("TkDefaultFont", 72)
        )
        icon_label.pack(pady=(0, 20))
        
        # Title
        title_label = ttk.Label(
            content_frame,
            text="Statistics",
            font=("TkDefaultFont", 24, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Coming soon message
        message_label = ttk.Label(
            content_frame,
            text="This feature is coming soon!",
            font=("TkDefaultFont", 14),
            foreground="gray"
        )
        message_label.pack(pady=(0, 20))
        
        # Description
        description_label = ttk.Label(
            content_frame,
            text="Statistics will show your personal scraping progress\nand global community contributions.",
            font=("TkDefaultFont", 11),
            foreground="gray",
            justify="center"
        )
        description_label.pack()
    
    def refresh_data(self):
        """Placeholder refresh method (does nothing)"""
        pass
