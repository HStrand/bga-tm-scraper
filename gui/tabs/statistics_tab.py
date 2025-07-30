"""
Statistics Tab for BGA TM Scraper GUI
Displays user and global statistics from the API with an appealing visual design
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StatisticsTab:
    """Statistics tab for displaying user and global statistics with visual appeal"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Statistics data
        self.statistics_data = None
        self.leaderboard_data = None
        self.is_loading = False
        
        # Create the UI
        self.create_widgets()
        
        # Load statistics on startup
        self.refresh_statistics()
    
    def create_widgets(self):
        """Create the statistics UI with visual appeal"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header frame
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Title with icon
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side="left")
        
        title_icon = ttk.Label(
            title_frame,
            text="📊",
            font=("TkDefaultFont", 20)
        )
        title_icon.pack(side="left", padx=(0, 10))
        
        title_label = ttk.Label(
            title_frame,
            text="Statistics",
            font=("TkDefaultFont", 18, "bold")
        )
        title_label.pack(side="left")
        
        # Right side of header
        header_right = ttk.Frame(header_frame)
        header_right.pack(side="right")
        
        # Last updated label
        self.last_updated_label = ttk.Label(
            header_right,
            text="",
            font=("TkDefaultFont", 9),
            foreground="gray"
        )
        self.last_updated_label.pack(side="left", padx=(0, 15))
        
        # Refresh button
        self.refresh_btn = ttk.Button(
            header_right,
            text="🔄 Refresh",
            command=self.refresh_statistics
        )
        self.refresh_btn.pack(side="left")
        
        # Content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Loading frame (initially hidden)
        self.loading_frame = ttk.Frame(content_frame)
        
        # Loading with spinner-like effect
        loading_container = ttk.Frame(self.loading_frame)
        loading_container.pack(expand=True)
        
        loading_icon = ttk.Label(
            loading_container,
            text="⏳",
            font=("TkDefaultFont", 24)
        )
        loading_icon.pack(pady=(0, 10))
        
        loading_label = ttk.Label(
            loading_container,
            text="Loading statistics...",
            font=("TkDefaultFont", 12),
            foreground="gray"
        )
        loading_label.pack()
        
        # Error frame (initially hidden)
        self.error_frame = ttk.Frame(content_frame)
        
        error_container = ttk.Frame(self.error_frame)
        error_container.pack(expand=True)
        
        error_icon = ttk.Label(
            error_container,
            text="⚠️",
            font=("TkDefaultFont", 24)
        )
        error_icon.pack(pady=(0, 10))
        
        self.error_label = ttk.Label(
            error_container,
            text="",
            font=("TkDefaultFont", 11),
            foreground="red",
            justify="center"
        )
        self.error_label.pack(pady=(0, 15))
        
        retry_btn = ttk.Button(
            error_container,
            text="🔄 Retry",
            command=self.refresh_statistics
        )
        retry_btn.pack()
        
        # Statistics frame (initially hidden)
        self.stats_frame = ttk.Frame(content_frame)
        
        # Overview cards section
        overview_frame = ttk.Frame(self.stats_frame)
        overview_frame.pack(fill="x", pady=(0, 25))
        
        overview_label = ttk.Label(
            overview_frame,
            text="Overview",
            font=("TkDefaultFont", 14, "bold")
        )
        overview_label.pack(anchor="w", pady=(0, 10))
        
        # Cards container
        self.cards_frame = ttk.Frame(overview_frame)
        self.cards_frame.pack(fill="x")
        
        # Details sections
        details_container = ttk.Frame(self.stats_frame)
        details_container.pack(fill="both", expand=True)
        
        # Left column - Your Contribution
        left_column = ttk.Frame(details_container)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        personal_frame = ttk.LabelFrame(
            left_column, 
            text="🎯 Your Contribution", 
            padding=15
        )
        personal_frame.pack(fill="both", expand=True)
        
        self.personal_stats_frame = ttk.Frame(personal_frame)
        self.personal_stats_frame.pack(fill="both", expand=True)

        # Leaderboard section
        leaderboard_frame = ttk.LabelFrame(
            left_column,
            text="🏆 Scraper Leaderboard",
            padding=15
        )
        leaderboard_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.leaderboard_tree = ttk.Treeview(
            leaderboard_frame,
            columns=("Rank", "Scraper", "Scraped Count"),
            show="headings"
        )
        self.leaderboard_tree.heading("Rank", text="#")
        self.leaderboard_tree.heading("Scraper", text="Scraper")
        self.leaderboard_tree.heading("Scraped Count", text="Scraped Count")
        self.leaderboard_tree.column("Rank", width=40, anchor="center")
        self.leaderboard_tree.column("Scraper", width=150)
        self.leaderboard_tree.column("Scraped Count", width=100, anchor="center")
        self.leaderboard_tree.pack(fill="both", expand=True)

        # Add styling for alternating row colors
        self.leaderboard_tree.tag_configure("oddrow", background="#f0f0f0")
        self.leaderboard_tree.tag_configure("evenrow", background="white")
        
        # Right column - Global Statistics
        right_column = ttk.Frame(details_container)
        right_column.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        global_frame = ttk.LabelFrame(
            right_column, 
            text="🌍 Global Statistics", 
            padding=15
        )
        global_frame.pack(fill="both", expand=True)
        
        self.global_stats_frame = ttk.Frame(global_frame)
        self.global_stats_frame.pack(fill="both", expand=True)
    
    def create_stat_card(self, parent, icon, value, label, color="#2563eb"):
        """Create a visually appealing statistics card"""
        card_frame = ttk.Frame(parent)
        card_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        # Card background (simulated with a frame and border)
        card_bg = ttk.Frame(card_frame, relief="solid", borderwidth=1)
        card_bg.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Card content
        card_content = ttk.Frame(card_bg)
        card_content.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Icon
        icon_label = ttk.Label(
            card_content,
            text=icon,
            font=("TkDefaultFont", 24)
        )
        icon_label.pack(pady=(0, 5))
        
        # Value
        value_label = ttk.Label(
            card_content,
            text=str(value),
            font=("TkDefaultFont", 18, "bold"),
            foreground=color
        )
        value_label.pack(pady=(0, 5))
        
        # Label
        label_label = ttk.Label(
            card_content,
            text=label,
            font=("TkDefaultFont", 9),
            foreground="gray",
            justify="center"
        )
        label_label.pack()
        
        return card_frame
    
    def show_loading(self):
        """Show loading state"""
        self.hide_all_frames()
        self.loading_frame.pack(fill="both", expand=True)
        self.refresh_btn.config(state="disabled", text="Loading...")
        self.last_updated_label.config(text="")
        self.frame.update()
    
    def show_error(self, error_message):
        """Show error state"""
        self.hide_all_frames()
        self.error_label.config(text=error_message)
        self.error_frame.pack(fill="both", expand=True)
        self.refresh_btn.config(state="normal", text="🔄 Refresh")
        self.last_updated_label.config(text="")
    
    def show_statistics(self):
        """Show statistics data"""
        self.hide_all_frames()
        self.populate_statistics()
        self.stats_frame.pack(fill="both", expand=True)
        self.refresh_btn.config(state="normal", text="🔄 Refresh")
        
        # Update last updated time
        current_time = datetime.now().strftime("%H:%M:%S")
        self.last_updated_label.config(text=f"Last updated: {current_time}")
    
    def hide_all_frames(self):
        """Hide all content frames"""
        self.loading_frame.pack_forget()
        self.error_frame.pack_forget()
        self.stats_frame.pack_forget()
    
    def refresh_statistics(self):
        """Refresh statistics data from API"""
        if self.is_loading:
            return
        
        # Validate configuration
        bga_email = self.config_manager.get_value("bga_credentials", "email", "")
        api_key = self.config_manager.get_value("api_settings", "api_key", "")
        
        if not bga_email:
            self.show_error("BGA email is not configured.\n\nPlease set it in Settings to view your statistics.")
            return
        
        if not api_key:
            self.show_error("API key is not configured.\n\nPlease set it in Settings to access the statistics API.")
            return
        
        # Show loading state
        self.show_loading()
        self.is_loading = True
        
        # Start API request in background thread
        api_thread = threading.Thread(target=self._fetch_statistics_from_api, daemon=True)
        api_thread.start()
    
    def _fetch_statistics_from_api(self):
        """Fetch statistics from the API in background thread"""
        try:
            # Get configuration
            api_key = self.config_manager.get_value("api_settings", "api_key")
            bga_email = self.config_manager.get_value("bga_credentials", "email")
            
            # Create API client
            from ..api_client import APIClient
            from ..version import BUILD_VERSION
            base_url = self.config_manager.get_value("api_settings", "base_url")
            api_client = APIClient(api_key, base_url=base_url, version=BUILD_VERSION)
            
            # Fetch statistics
            statistics_data = api_client.get_statistics(bga_email)
            leaderboard_data = api_client.get_scraper_leaderboard()
            
            if statistics_data:
                self.statistics_data = statistics_data
                self.leaderboard_data = leaderboard_data
                self.frame.after(0, self.show_statistics)
            else:
                self.frame.after(0, lambda: self.show_error(
                    "No statistics data available.\n\n"
                    "This could mean:\n"
                    "• You haven't scraped any games yet\n"
                    "• There's an issue with the API\n"
                    "• Your email is not recognized in the system"
                ))
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error fetching statistics: {e}")
            
            if "network" in error_msg.lower() or "connection" in error_msg.lower():
                error_text = "Network error occurred.\n\nPlease check your internet connection and try again."
            elif "timeout" in error_msg.lower():
                error_text = "Request timed out.\n\nThe server might be busy. Please try again in a moment."
            elif "401" in error_msg or "403" in error_msg:
                error_text = "Authentication failed.\n\nPlease check your API key in Settings."
            else:
                error_text = f"Error loading statistics:\n\n{error_msg}"
            
            self.frame.after(0, lambda: self.show_error(error_text))
        
        finally:
            self.is_loading = False
    
    def populate_statistics(self):
        """Populate the statistics display with data"""
        if not self.statistics_data:
            return
        
        # Clear existing widgets
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
        for widget in self.personal_stats_frame.winfo_children():
            widget.destroy()
        for widget in self.global_stats_frame.winfo_children():
            widget.destroy()
        
        # Create overview cards
        personal_games = self.statistics_data.get("scrapedGamesByUser", 0)
        total_scraped = self.statistics_data.get("scrapedGamesTotal", 0)
        total_indexed = self.statistics_data.get("totalIndexedGames", 0)
        total_players = self.statistics_data.get("totalPlayers", 0)
        
        # Calculate contribution percentage
        contribution_pct = (personal_games / max(total_scraped, 1)) * 100 if total_scraped > 0 else 0
        
        # Create cards
        self.create_stat_card(
            self.cards_frame, 
            "🎯", 
            f"{personal_games:,}", 
            "Games Scraped\nby You", 
            "#059669"
        )
        
        self.create_stat_card(
            self.cards_frame, 
            "📋", 
            f"{total_scraped:,}", 
            "Total Scraped\nGames", 
            "#2563eb"
        )
        
        self.create_stat_card(
            self.cards_frame, 
            "📊", 
            f"{total_indexed:,}", 
            "Total Indexed\nGames", 
            "#7c3aed"
        )
        
        self.create_stat_card(
            self.cards_frame, 
            "✅", 
            f"{contribution_pct:.1f}%", 
            "Your Contribution\nPercentage", 
            "#dc2626"
        )
        
        # Personal statistics section
        self.create_detail_section(
            self.personal_stats_frame,
            [
                ("Games Scraped by You", f"{personal_games:,}", "🎯", "#059669"),
                ("Your Contribution", f"{contribution_pct:.1f}%", "📈", "#059669"),
            ]
        )
        
        # Add motivational message
        if personal_games > 0:
            motivation_frame = ttk.Frame(self.personal_stats_frame)
            motivation_frame.pack(fill="x", pady=(15, 0))
            
            if personal_games >= 2000:
                message = "🌟 Amazing contributor! Thank you for your dedication!"
                color = "#059669"
            elif personal_games >= 1000:
                message = "🚀 Great work! You're making a real impact!"
                color = "#2563eb"
            elif personal_games >= 150:
                message = "👍 Nice progress! Keep up the good work!"
                color = "#7c3aed"
            else:
                message = "🎉 Welcome to the community! Every game counts!"
                color = "#dc2626"
            
            motivation_label = ttk.Label(
                motivation_frame,
                text=message,
                font=("TkDefaultFont", 10, "italic"),
                foreground=color,
                justify="center"
            )
            motivation_label.pack()
        
        # Populate leaderboard
        if self.leaderboard_data:
            for item in self.leaderboard_tree.get_children():
                self.leaderboard_tree.delete(item)
            for i, scraper_data in enumerate(self.leaderboard_data):
                tag = "evenrow" if i % 2 == 0 else "oddrow"
                self.leaderboard_tree.insert("", "end", values=(i + 1, scraper_data["scraper"], scraper_data["scrapedCount"]), tags=(tag,))

        # Global statistics section
        avg_elo = self.statistics_data.get("averageEloInScrapedGames", 0)
        median_elo = self.statistics_data.get("medianEloInScrapedGames", 0)
        
        self.create_detail_section(
            self.global_stats_frame,
            [
                ("Total Players", f"{total_players:,}", "👥", "#2563eb"),
                ("Total Indexed Games", f"{total_indexed:,}", "📊", "#2563eb"),
                ("Total Scraped Games", f"{total_scraped:,}", "📋", "#2563eb"),
                ("Average ELO in Scraped Games", f"{avg_elo:,}", "📈", "#7c3aed"),
                ("Median ELO in Scraped Games", f"{median_elo:,}", "📊", "#7c3aed"),
            ]
        )
    
    def create_detail_section(self, parent, stats_data):
        """Create a detailed statistics section"""
        for i, (label, value, icon, color) in enumerate(stats_data):
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill="x", pady=8)
            
            # Icon and label
            label_frame = ttk.Frame(row_frame)
            label_frame.pack(side="left", fill="x", expand=True)
            
            icon_label = ttk.Label(
                label_frame,
                text=icon,
                font=("TkDefaultFont", 14)
            )
            icon_label.pack(side="left", padx=(0, 10))
            
            text_label = ttk.Label(
                label_frame,
                text=label,
                font=("TkDefaultFont", 11)
            )
            text_label.pack(side="left")
            
            # Value
            value_label = ttk.Label(
                row_frame,
                text=value,
                font=("TkDefaultFont", 12, "bold"),
                foreground=color
            )
            value_label.pack(side="right")
            
            # Add separator line (except for last item)
            if i < len(stats_data) - 1:
                separator = ttk.Separator(parent, orient="horizontal")
                separator.pack(fill="x", pady=5)
    
    def refresh_data(self):
        """Public method to refresh data (called by main window)"""
        self.refresh_statistics()
