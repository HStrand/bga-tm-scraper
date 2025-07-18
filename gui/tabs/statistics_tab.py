"""
Statistics Tab for BGA TM Scraper GUI
Displays personal and global scraping statistics with simple charts
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
from datetime import datetime, timedelta


class StatisticsTab:
    """Statistics tab for displaying scraping metrics"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Mock data for statistics
        self.personal_stats = self._generate_mock_personal_stats()
        self.global_stats = self._generate_mock_global_stats()
        
        # Create the UI
        self.create_widgets()
        
        # Load initial data
        self.refresh_data()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title and refresh button
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ttk.Label(header_frame, text="Statistics", 
                               font=("TkDefaultFont", 16, "bold"))
        title_label.pack(side="left")
        
        self.refresh_btn = ttk.Button(
            header_frame,
            text="🔄 Refresh",
            command=self.refresh_data
        )
        self.refresh_btn.pack(side="right")
        
        # Last updated label
        self.last_updated_label = ttk.Label(
            header_frame,
            text="Last updated: Never",
            foreground="gray",
            font=("TkDefaultFont", 9)
        )
        self.last_updated_label.pack(side="right", padx=(0, 10))
        
        # Create notebook for personal vs global stats
        self.stats_notebook = ttk.Notebook(main_frame)
        self.stats_notebook.pack(fill="both", expand=True)
        
        # Personal statistics tab
        self.personal_frame = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(self.personal_frame, text="👤 Personal Stats")
        self.create_personal_stats(self.personal_frame)
        
        # Global statistics tab
        self.global_frame = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(self.global_frame, text="🌍 Global Stats")
        self.create_global_stats(self.global_frame)
    
    def create_personal_stats(self, parent):
        """Create personal statistics section"""
        # Scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Personal stats content
        content_frame = ttk.Frame(scrollable_frame)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Overview section
        overview_frame = ttk.LabelFrame(content_frame, text="Overview", padding=15)
        overview_frame.pack(fill="x", pady=(0, 20))
        
        # Create overview grid
        overview_grid = ttk.Frame(overview_frame)
        overview_grid.pack(fill="x")
        
        # Configure grid columns
        for i in range(4):
            overview_grid.columnconfigure(i, weight=1)
        
        # Overview stats
        self.personal_overview_widgets = {}
        overview_stats = [
            ("Games Indexed", "games_indexed", "🔍"),
            ("Logs Collected", "logs_collected", "📋"),
            ("Total Contributions", "total_contributions", "🎯"),
            ("Success Rate", "success_rate", "✅")
        ]
        
        for i, (label, key, icon) in enumerate(overview_stats):
            stat_frame = ttk.Frame(overview_grid)
            stat_frame.grid(row=0, column=i, padx=10, pady=5, sticky="ew")
            
            icon_label = ttk.Label(stat_frame, text=icon, font=("TkDefaultFont", 20))
            icon_label.pack()
            
            value_label = ttk.Label(stat_frame, text="0", font=("TkDefaultFont", 16, "bold"))
            value_label.pack()
            
            desc_label = ttk.Label(stat_frame, text=label, font=("TkDefaultFont", 9))
            desc_label.pack()
            
            self.personal_overview_widgets[key] = value_label
        
        # Recent activity section
        activity_frame = ttk.LabelFrame(content_frame, text="Recent Activity", padding=15)
        activity_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Activity list
        self.activity_tree = ttk.Treeview(
            activity_frame,
            columns=("Date", "Type", "Count", "Status"),
            show="headings",
            height=8
        )
        
        # Configure columns
        self.activity_tree.heading("Date", text="Date")
        self.activity_tree.heading("Type", text="Activity Type")
        self.activity_tree.heading("Count", text="Items")
        self.activity_tree.heading("Status", text="Status")
        
        self.activity_tree.column("Date", width=100)
        self.activity_tree.column("Type", width=150)
        self.activity_tree.column("Count", width=80)
        self.activity_tree.column("Status", width=100)
        
        # Activity scrollbar
        activity_scrollbar = ttk.Scrollbar(activity_frame, orient="vertical", command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=activity_scrollbar.set)
        
        self.activity_tree.pack(side="left", fill="both", expand=True)
        activity_scrollbar.pack(side="right", fill="y")
        
        # Performance chart section
        chart_frame = ttk.LabelFrame(content_frame, text="Performance Chart", padding=15)
        chart_frame.pack(fill="both", expand=True)
        
        # Simple canvas-based chart
        self.personal_chart_canvas = tk.Canvas(
            chart_frame,
            height=200,
            bg="white",
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.personal_chart_canvas.pack(fill="both", expand=True, pady=10)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_global_stats(self, parent):
        """Create global statistics section"""
        # Main content frame
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Global overview section
        global_overview_frame = ttk.LabelFrame(content_frame, text="Community Overview", padding=15)
        global_overview_frame.pack(fill="x", pady=(0, 20))
        
        # Create global overview grid
        global_grid = ttk.Frame(global_overview_frame)
        global_grid.pack(fill="x")
        
        # Configure grid columns
        for i in range(4):
            global_grid.columnconfigure(i, weight=1)
        
        # Global overview stats
        self.global_overview_widgets = {}
        global_overview_stats = [
            ("Total Games", "total_games", "🎮"),
            ("Active Contributors", "active_contributors", "👥"),
            ("Data Coverage", "data_coverage", "📊"),
            ("Daily Growth", "daily_growth", "📈")
        ]
        
        for i, (label, key, icon) in enumerate(global_overview_stats):
            stat_frame = ttk.Frame(global_grid)
            stat_frame.grid(row=0, column=i, padx=10, pady=5, sticky="ew")
            
            icon_label = ttk.Label(stat_frame, text=icon, font=("TkDefaultFont", 20))
            icon_label.pack()
            
            value_label = ttk.Label(stat_frame, text="0", font=("TkDefaultFont", 16, "bold"))
            value_label.pack()
            
            desc_label = ttk.Label(stat_frame, text=label, font=("TkDefaultFont", 9))
            desc_label.pack()
            
            self.global_overview_widgets[key] = value_label
        
        # Top contributors section
        contributors_frame = ttk.LabelFrame(content_frame, text="Top Contributors", padding=15)
        contributors_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Contributors list
        self.contributors_tree = ttk.Treeview(
            contributors_frame,
            columns=("Rank", "Contributor", "Games", "Logs", "Total"),
            show="headings",
            height=10
        )
        
        # Configure columns
        self.contributors_tree.heading("Rank", text="Rank")
        self.contributors_tree.heading("Contributor", text="Contributor")
        self.contributors_tree.heading("Games", text="Games Indexed")
        self.contributors_tree.heading("Logs", text="Logs Collected")
        self.contributors_tree.heading("Total", text="Total")
        
        self.contributors_tree.column("Rank", width=60)
        self.contributors_tree.column("Contributor", width=150)
        self.contributors_tree.column("Games", width=120)
        self.contributors_tree.column("Logs", width=120)
        self.contributors_tree.column("Total", width=100)
        
        # Contributors scrollbar
        contributors_scrollbar = ttk.Scrollbar(contributors_frame, orient="vertical", command=self.contributors_tree.yview)
        self.contributors_tree.configure(yscrollcommand=contributors_scrollbar.set)
        
        self.contributors_tree.pack(side="left", fill="both", expand=True)
        contributors_scrollbar.pack(side="right", fill="y")
        
        # Global chart section
        global_chart_frame = ttk.LabelFrame(content_frame, text="Global Activity Chart", padding=15)
        global_chart_frame.pack(fill="both", expand=True)
        
        # Simple canvas-based chart
        self.global_chart_canvas = tk.Canvas(
            global_chart_frame,
            height=200,
            bg="white",
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.global_chart_canvas.pack(fill="both", expand=True, pady=10)
    
    def refresh_data(self):
        """Refresh statistics data (mock implementation)"""
        # Disable refresh button temporarily
        self.refresh_btn.config(state="disabled", text="Refreshing...")
        
        # Simulate API delay
        self.frame.after(1500, self._update_data)
    
    def _update_data(self):
        """Update the statistics data (mock)"""
        try:
            # Generate new mock data
            self.personal_stats = self._generate_mock_personal_stats()
            self.global_stats = self._generate_mock_global_stats()
            
            # Update personal stats
            self._update_personal_stats()
            
            # Update global stats
            self._update_global_stats()
            
            # Update charts
            self._draw_personal_chart()
            self._draw_global_chart()
            
            # Update last updated time
            self.last_updated_label.config(
                text=f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
            )
            
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to refresh statistics:\n{str(e)}")
        
        finally:
            # Re-enable refresh button
            self.refresh_btn.config(state="normal", text="🔄 Refresh")
    
    def _update_personal_stats(self):
        """Update personal statistics widgets"""
        stats = self.personal_stats
        
        # Update overview widgets
        self.personal_overview_widgets["games_indexed"].config(text=f"{stats['games_indexed']:,}")
        self.personal_overview_widgets["logs_collected"].config(text=f"{stats['logs_collected']:,}")
        self.personal_overview_widgets["total_contributions"].config(text=f"{stats['total_contributions']:,}")
        self.personal_overview_widgets["success_rate"].config(text=f"{stats['success_rate']:.1f}%")
        
        # Update activity tree
        # Clear existing items
        for item in self.activity_tree.get_children():
            self.activity_tree.delete(item)
        
        # Add recent activities
        for activity in stats["recent_activities"]:
            self.activity_tree.insert("", "end", values=(
                activity["date"],
                activity["type"],
                activity["count"],
                activity["status"]
            ))
    
    def _update_global_stats(self):
        """Update global statistics widgets"""
        stats = self.global_stats
        
        # Update global overview widgets
        self.global_overview_widgets["total_games"].config(text=f"{stats['total_games']:,}")
        self.global_overview_widgets["active_contributors"].config(text=f"{stats['active_contributors']:,}")
        self.global_overview_widgets["data_coverage"].config(text=f"{stats['data_coverage']:.1f}%")
        self.global_overview_widgets["daily_growth"].config(text=f"+{stats['daily_growth']:,}")
        
        # Update contributors tree
        # Clear existing items
        for item in self.contributors_tree.get_children():
            self.contributors_tree.delete(item)
        
        # Add top contributors
        for i, contributor in enumerate(stats["top_contributors"], 1):
            self.contributors_tree.insert("", "end", values=(
                f"#{i}",
                contributor["name"],
                f"{contributor['games']:,}",
                f"{contributor['logs']:,}",
                f"{contributor['total']:,}"
            ))
    
    def _draw_personal_chart(self):
        """Draw personal performance chart"""
        canvas = self.personal_chart_canvas
        canvas.delete("all")
        
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            # Canvas not ready yet
            self.frame.after(100, self._draw_personal_chart)
            return
        
        # Chart data (last 7 days)
        data = self.personal_stats["daily_performance"]
        
        if not data:
            canvas.create_text(width//2, height//2, text="No data available", fill="gray")
            return
        
        # Chart margins
        margin_left = 50
        margin_right = 20
        margin_top = 20
        margin_bottom = 40
        
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        
        # Find max value for scaling
        max_value = max(max(day["games"], day["logs"]) for day in data)
        if max_value == 0:
            max_value = 1
        
        # Draw axes
        canvas.create_line(margin_left, height - margin_bottom, 
                          width - margin_right, height - margin_bottom, 
                          fill="black", width=2)  # X-axis
        canvas.create_line(margin_left, margin_top, 
                          margin_left, height - margin_bottom, 
                          fill="black", width=2)  # Y-axis
        
        # Draw bars
        bar_width = chart_width / (len(data) * 2)
        
        for i, day_data in enumerate(data):
            x = margin_left + (i * 2 + 0.5) * bar_width
            
            # Games bar (blue)
            games_height = (day_data["games"] / max_value) * chart_height
            canvas.create_rectangle(
                x, height - margin_bottom - games_height,
                x + bar_width * 0.8, height - margin_bottom,
                fill="#4CAF50", outline="black"
            )
            
            # Logs bar (green)
            logs_height = (day_data["logs"] / max_value) * chart_height
            canvas.create_rectangle(
                x + bar_width * 0.8, height - margin_bottom - logs_height,
                x + bar_width * 1.6, height - margin_bottom,
                fill="#2196F3", outline="black"
            )
            
            # Day label
            canvas.create_text(
                x + bar_width * 0.8, height - margin_bottom + 15,
                text=day_data["day"], font=("TkDefaultFont", 8)
            )
        
        # Legend
        canvas.create_rectangle(width - 150, 20, width - 140, 30, fill="#4CAF50")
        canvas.create_text(width - 130, 25, text="Games Indexed", anchor="w", font=("TkDefaultFont", 8))
        
        canvas.create_rectangle(width - 150, 35, width - 140, 45, fill="#2196F3")
        canvas.create_text(width - 130, 40, text="Logs Collected", anchor="w", font=("TkDefaultFont", 8))
    
    def _draw_global_chart(self):
        """Draw global activity chart"""
        canvas = self.global_chart_canvas
        canvas.delete("all")
        
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            # Canvas not ready yet
            self.frame.after(100, self._draw_global_chart)
            return
        
        # Chart data (last 30 days trend)
        data = self.global_stats["monthly_trend"]
        
        if not data:
            canvas.create_text(width//2, height//2, text="No data available", fill="gray")
            return
        
        # Chart margins
        margin_left = 50
        margin_right = 20
        margin_top = 20
        margin_bottom = 40
        
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        
        # Find max value for scaling
        max_value = max(data)
        if max_value == 0:
            max_value = 1
        
        # Draw axes
        canvas.create_line(margin_left, height - margin_bottom, 
                          width - margin_right, height - margin_bottom, 
                          fill="black", width=2)  # X-axis
        canvas.create_line(margin_left, margin_top, 
                          margin_left, height - margin_bottom, 
                          fill="black", width=2)  # Y-axis
        
        # Draw line chart
        points = []
        for i, value in enumerate(data):
            x = margin_left + (i / (len(data) - 1)) * chart_width
            y = height - margin_bottom - (value / max_value) * chart_height
            points.extend([x, y])
            
            # Draw point
            canvas.create_oval(x-3, y-3, x+3, y+3, fill="#FF5722", outline="black")
        
        # Draw line
        if len(points) >= 4:
            canvas.create_line(points, fill="#FF5722", width=2, smooth=True)
        
        # Y-axis labels
        for i in range(5):
            y = height - margin_bottom - (i / 4) * chart_height
            value = (i / 4) * max_value
            canvas.create_text(margin_left - 10, y, text=f"{int(value)}", anchor="e", font=("TkDefaultFont", 8))
        
        # Title
        canvas.create_text(width//2, 10, text="Daily Contributions (Last 30 Days)", 
                          font=("TkDefaultFont", 10, "bold"))
    
    def _generate_mock_personal_stats(self):
        """Generate mock personal statistics"""
        return {
            "games_indexed": random.randint(50, 500),
            "logs_collected": random.randint(20, 200),
            "total_contributions": random.randint(70, 700),
            "success_rate": random.uniform(85.0, 98.0),
            "recent_activities": [
                {
                    "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
                    "type": random.choice(["Index Games", "Collect Logs"]),
                    "count": random.randint(5, 50),
                    "status": random.choice(["Completed", "In Progress", "Failed"])
                }
                for i in range(10)
            ],
            "daily_performance": [
                {
                    "day": (datetime.now() - timedelta(days=i)).strftime("%m/%d"),
                    "games": random.randint(0, 20),
                    "logs": random.randint(0, 15)
                }
                for i in range(7, 0, -1)
            ]
        }
    
    def _generate_mock_global_stats(self):
        """Generate mock global statistics"""
        return {
            "total_games": random.randint(50000, 100000),
            "active_contributors": random.randint(50, 200),
            "data_coverage": random.uniform(65.0, 85.0),
            "daily_growth": random.randint(100, 1000),
            "top_contributors": [
                {
                    "name": f"Contributor_{i}",
                    "games": random.randint(500, 5000),
                    "logs": random.randint(200, 2000),
                    "total": random.randint(700, 7000)
                }
                for i in range(1, 11)
            ],
            "monthly_trend": [random.randint(50, 500) for _ in range(30)]
        }
