import tkinter as tk
from tkinter import ttk, filedialog
# from ..components import ScrollableFrame


class AnalysisTab:
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager

        # Create main frame
        self.frame = ttk.Frame(parent)
        # self.scrollable = ScrollableFrame(self.frame)
        # self.scrollable.pack(fill=tk.BOTH, expand=True)
        # self.content = self.scrollable.scrollable_frame

        # File selection section
        self.create_file_selection()

        # Filter section
        self.create_filters()

        # Analysis button and results section
        self.create_analysis_section()

    def create_file_selection(self):
        file_frame = ttk.LabelFrame(self.content, text="Data Source", padding=10)
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        # File path entry and browse button
        path_frame = ttk.Frame(file_frame)
        path_frame.pack(fill=tk.X)

        self.file_path_var = tk.StringVar()
        self.file_path_entry = ttk.Entry(path_frame, textvariable=self.file_path_var)
        self.file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_button = ttk.Button(path_frame, text="Browse", command=self.browse_file)
        browse_button.pack(side=tk.RIGHT)

    def create_filters(self):
        filter_frame = ttk.LabelFrame(self.content, text="Filters", padding=10)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        # Create filter fields
        self.filters = {
            "Player ID": self.create_filter_field(filter_frame, "Player ID"),
            "Player min. Elo": self.create_filter_field(filter_frame, "Player min. Elo"),
            "Opponent min. Elo": self.create_filter_field(filter_frame, "Opponent min. Elo"),
            "Corporation": self.create_filter_field(filter_frame, "Corporation", is_dropdown=True),
            "Starting Hand Option": self.create_filter_field(filter_frame, "Starting Hand Option", is_dropdown=True),
            "Card Played": self.create_filter_field(filter_frame, "Card Played", is_dropdown=True)
        }

    def create_filter_field(self, parent, label, is_dropdown=False):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)

        # Checkbox to enable/disable the filter
        var_enabled = tk.BooleanVar(value=False)
        checkbox = ttk.Checkbutton(frame, text=label, variable=var_enabled)
        checkbox.pack(side=tk.LEFT)

        # Entry or Combobox for the filter value
        if is_dropdown:
            var_value = ttk.Combobox(frame, state="readonly")
            var_value["values"] = []  # To be populated later
        else:
            var_value = ttk.Entry(frame)
        var_value.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        return {"enabled": var_enabled, "value": var_value}

    def create_analysis_section(self):
        analysis_frame = ttk.LabelFrame(self.content, text="Analysis", padding=10)
        analysis_frame.pack(fill=tk.X, padx=5, pady=5)

        # Analyze button
        analyze_button = ttk.Button(analysis_frame, text="Analyze!", command=self.run_analysis)
        analyze_button.pack(fill=tk.X, pady=5)

        # Results section
        results_frame = ttk.Frame(analysis_frame)
        results_frame.pack(fill=tk.X)

        # Win rate result
        ttk.Label(results_frame, text="Win Rate:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.win_rate_var = tk.StringVar(value="-")
        ttk.Label(results_frame, textvariable=self.win_rate_var).grid(row=0, column=1, sticky=tk.W, padx=5)

        # Elo change result
        ttk.Label(results_frame, text="Elo Change:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.elo_change_var = tk.StringVar(value="-")
        ttk.Label(results_frame, textvariable=self.elo_change_var).grid(row=1, column=1, sticky=tk.W, padx=5)

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select data file",
            filetypes=[("ZIP files", "*.zip")]
        )
        if filename:
            self.file_path_var.set(filename)

    def run_analysis(self):
        # This function will be implemented later
        pass