import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import zipfile
import json
import threading

class AutocompleteCombobox(ttk.Combobox):

    def set_completion_list(self, completion_list):
        """Use our completion list as our drop down selection menu, arrows move through menu."""
        self._completion_list = sorted(completion_list, key=str.lower)  # Work with a sorted list
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)
        self['values'] = self._completion_list  # Setup our popup menu

    def autocomplete(self, delta=0):
        """autocomplete the Combobox, delta may be 0/1/-1 to cycle through possible hits"""
        if delta:  # need to delete selection otherwise we would fix the current position
            self.delete(self.position, tk.END)
        else:  # set position to end so selection starts where textentry ended
            self.position = len(self.get())
        # collect hits
        _hits = []
        for element in self._completion_list:
            if element.lower().startswith(self.get().lower()):  # Match case insensitively
                _hits.append(element)
        # if we have a new hit list, keep this in mind
        if _hits != self._hits:
            self._hit_index = 0
            self._hits = _hits
        # only allow cycling if we are in a known hit list
        if _hits == self._hits and self._hits:
            self._hit_index = (self._hit_index + delta) % len(self._hits)
        # now finally perform the auto completion
        if self._hits:
            self.delete(0, tk.END)
            self.insert(0, self._hits[self._hit_index])
            self.select_range(self.position, tk.END)

    def handle_keyrelease(self, event):
        """event handler for the keyrelease event on this widget"""
        if event.keysym == "BackSpace":
            self.delete(self.index(tk.INSERT), tk.END)
            self.position = self.index(tk.END)
        if event.keysym == "Left":
            if self.position < self.index(tk.END):  # delete the selection
                self.delete(self.position, tk.END)
            else:
                self.position = self.position - 1  # delete one character
                self.delete(self.position, tk.END)
        if event.keysym == "Right":
            self.position = self.index(tk.END)  # go to end (no selection)
        if len(event.keysym) == 1:
            self.autocomplete()
        # No need for up/down, we'll jump to the popup
        # list at the position of the autocompletion

class AnalysisTab:

    corporations = ["Valley Trust",
                    "Mining Guild",
                    "Point Luna",
                    "Robinson Industries",
                    "Cheung Shing Mars",
                    "Interplanetary Cinematics",
                    "Tharsis Republic",
                    "Saturn Systems",
                    "CrediCor",
                    "Ecoline",
                    "Helion",
                    "Inventrix",
                    "PhoboLog",
                    "Teractor",
                    "ThorGate",
                    "United Nations Mars Initiative",
                    "Vitor"]



    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager

        # Create main frame
        self.frame = ttk.Frame(parent)

        # Add canvas and scrollbar
        self.canvas = tk.Canvas(self.frame)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack scrollbar and canvas
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = self.scrollable_frame

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
            "Opponent ID": self.create_filter_field(filter_frame, "Opponent ID"),
            "Player min. Elo": self.create_filter_field(filter_frame, "Player min. Elo"),
            "Player max. Elo": self.create_filter_field(filter_frame, "Player max. Elo"),
            "Opponent min. Elo": self.create_filter_field(filter_frame, "Opponent min. Elo"),
            "Opponent max. Elo": self.create_filter_field(filter_frame, "Opponent max. Elo"),
            "Corporation": self.create_filter_field(filter_frame, "Corporation", values=self.corporations)
            #"Starting Hand Option": self.create_filter_field(filter_frame, "Starting Hand Option"),
            #"Card Played": self.create_filter_field(filter_frame, "Card Played")
        }

    def create_filter_field(self, parent, label, values=[]):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)

        # Checkbox to enable/disable the filter
        var_enabled = tk.BooleanVar(value=False)
        checkbox = ttk.Checkbutton(frame, text=label, variable=var_enabled)
        checkbox.grid(row=0, column=0, sticky=tk.W)

        # Entry or Combobox for the filter value
        if values:
            var_value = AutocompleteCombobox(frame, width=27)
            var_value["values"] = values  # To be populated later
            var_value.set_completion_list(values)
        else:
            var_value = ttk.Entry(frame, width=30)
        var_value.grid(row=0, column=1, sticky=tk.E, padx=5)

        frame.columnconfigure(1, weight=1)

        return {"enabled": var_enabled, "value": var_value}

    def create_analysis_section(self):
        analysis_frame = ttk.LabelFrame(self.content, text="Note: Win rate and Elo change refer to player 1 of the replays", padding=5)
        analysis_frame.pack(fill=tk.X, padx=5, pady=5)

        # Analyze button
        analyze_button = ttk.Button(analysis_frame, text="Analyze!", command=self.run_analysis)
        analyze_button.pack(fill=tk.X, pady=5)

        # Progress section
        progress_frame = ttk.Frame(analysis_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(progress_frame, text="0 / 0 (0%)")
        self.progress_label.pack()

        # Results section
        results_frame = ttk.Frame(analysis_frame)
        results_frame.pack(fill=tk.X)

        
        # Win rate result
        ttk.Label(results_frame, text="Win Rate:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.win_rate_var = tk.StringVar(value="-")
        ttk.Label(results_frame, textvariable=self.win_rate_var).grid(row=0, column=1, sticky=tk.W, padx=5)

        # Elo change result
        ttk.Label(results_frame, text="Avg. Elo Change:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.elo_change_var = tk.StringVar(value="-")
        ttk.Label(results_frame, textvariable=self.elo_change_var).grid(row=1, column=1, sticky=tk.W, padx=5)

        # Replay IDs section
        ttk.Label(results_frame, text="Replay IDs:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.replay_ids_text = scrolledtext.ScrolledText(results_frame, width=40, height=4, wrap=tk.WORD)
        self.replay_ids_text.grid(row=2, column=1, sticky=tk.W, padx=5)
        self.replay_ids_text.insert('1.0', '-')

        # Card win rates section
        ttk.Label(results_frame, text="Starting Keeps Win Rates:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.card_win_rates_text = scrolledtext.ScrolledText(results_frame, width=40, height=10, wrap=tk.WORD)
        self.card_win_rates_text.grid(row=3, column=1, sticky=tk.W, padx=5)
        self.card_win_rates_text.insert('1.0', '-')

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select data file",
            filetypes=[("ZIP files", "*.zip")]
        )
        if filename:
            self.file_path_var.set(filename)

    def run_analysis(self):
        # Check if file is selected
        if not self.file_path_var.get():
            tk.messagebox.showerror("Error", "Please select a data source ZIP file first")
            return

        # Reset progress
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Counting files...")
        
        # Start analysis in a separate thread
        threading.Thread(target=self._run_analysis_thread, daemon=True).start()

    def _run_analysis_thread(self):
        try:
            with zipfile.ZipFile(self.file_path_var.get(), 'r') as zip_ref:
                # Count total JSON files first
                json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
                total_files = len(json_files)
                processed_files = 0

                # Initialize analysis variables
                total_games = 0
                wins = 0
                total_elo_change = 0
                matching_replay_ids = []
                card_wins = {}
                card_games = {}

                # Update initial progress
                self._update_progress(processed_files, total_files)

                # Process each file
                for file_name in json_files:
                    with zip_ref.open(file_name) as json_file:

                        processed_files += 1
                        self._update_progress(processed_files, total_files)

                        try:
                            data = json.load(json_file)
                            print("File name: " + file_name + ", Replay ID: " + str(data.get("replay_id")))

                            # Only look at 2 player games including elo data
                            if data.get("metadata").get("elo_players_found") !=  2 or data.get("metadata").get("elo_data_included") == False:
                                continue

                            # Hero ID filter
                            if self.filters["Player ID"]["enabled"].get():
                                player_id = self.filters["Player ID"]["value"].get()
                                if str(data.get("player_perspective")) != player_id:
                                    continue

                            # Opponent ID filter
                            if self.filters["Opponent ID"]["enabled"].get():
                                opponent_id = self.filters["Opponent ID"]["value"].get()
                                if str(data.get("player_perspective")) == opponent_id or not any(str(player) == opponent_id for player in data.get("players", [])):
                                    continue

                            # Hero min. Elo filter
                            if self.filters["Player min. Elo"]["enabled"].get():
                                min_elo = int(self.filters["Player min. Elo"]["value"].get())
                                player_perspective = str(data.get("player_perspective"))
                                player_elo = -1
                                elo_data = data.get("players").get(player_perspective).get("elo_data")
                                if elo_data: # Hero can have no Elo
                                    player_elo = data.get("players").get(player_perspective).get("elo_data").get("game_rank")
                                if player_elo < min_elo:
                                    print("Hero Elo too low")
                                    continue
                                else:
                                    print("Hero Elo OK")

                            # Hero max. Elo filter
                            if self.filters["Player max. Elo"]["enabled"].get():
                                max_elo = int(self.filters["Player max. Elo"]["value"].get())
                                player_perspective = str(data.get("player_perspective"))
                                player_elo = -1
                                elo_data = data.get("players").get(player_perspective).get("elo_data")
                                if elo_data:  # Hero can have no Elo
                                    player_elo = data.get("players").get(player_perspective).get("elo_data").get("game_rank")
                                if player_elo > max_elo:
                                    print("Hero Elo too high")
                                    continue
                                else:
                                    print("Hero Elo OK")

                            # Opponent min. Elo filter
                            if self.filters["Opponent min. Elo"]["enabled"].get():
                                min_elo = int(self.filters["Opponent min. Elo"]["value"].get())
                                player_perspective = str(data.get("player_perspective"))
                                players = data.get("players")
                                opponent_elo = -1
                                for player in players:
                                    if player != player_perspective:
                                        elo_data = players.get(player).get("elo_data")
                                        if elo_data: # Opponent can have no Elo
                                            opponent_elo = elo_data.get("game_rank")
                                            print(f"Opponent Elo: {opponent_elo}, Min Elo: {min_elo}")

                                if opponent_elo < min_elo:
                                    print("Opponent Elo too low")
                                    continue
                                else:
                                    print("Opponent Elo OK")

                            #Opponent max. Elo filter
                            if self.filters["Opponent max. Elo"]["enabled"].get():
                                max_elo = int(self.filters["Opponent max. Elo"]["value"].get())
                                player_perspective = str(data.get("player_perspective"))
                                players = data.get("players")
                                opponent_elo = -1
                                for player in players:
                                    if player != player_perspective:
                                        elo_data = players.get(player).get("elo_data")
                                        if elo_data:  # Opponent can have no Elo
                                            opponent_elo = elo_data.get("game_rank")
                                            print(f"Opponent Elo: {opponent_elo}, Max Elo: {max_elo}")

                                if opponent_elo > max_elo:
                                    print("Opponent Elo too high")
                                    continue
                                else:
                                    print("Opponent Elo OK")


                            # Corporation filter
                            if self.filters["Corporation"]["enabled"].get():
                                corporation = self.filters["Corporation"]["value"].get()
                                player_perspective = data.get("player_perspective")
                                if corporation != data.get("players").get(player_perspective).get("corporation"):
                                    continue

                            # If all filters pass, analyze the game
                            total_games += 1
                            matching_replay_ids.append(data.get("replay_id"))
                            print(f"Game passed all filters: {file_name}")

                            # Get card keeps
                            keeps = []
                            if data.get("moves") and len(data.get("moves")) > 1: # Game can end without moves
                                description = str(data.get("moves")[1]) # Get description of 2nd move
                                for string in description.split(" | "):
                                    if string.startswith("You buy"):
                                        keeps.append(string[8:])
                            for keep in keeps:
                                if keep not in card_games:
                                    card_games[keep] = 0
                                card_games[keep] += 1

                            # Check if Hero won
                            player_perspective = str(data.get("player_perspective"))
                            if data.get("players", []).get(player_perspective).get("player_name") == data.get("winner"):
                                print("Hero won!")
                                wins += 1
                                for keep in keeps:
                                    if keep not in card_wins:
                                        card_wins[keep] = 0
                                    card_wins[keep] += 1
                            else:
                                print("Hero lost!")

                            elo_data = data.get("players").get(player_perspective).get("elo_data")
                            if elo_data:
                                total_elo_change += elo_data.get("game_rank_change")
                            

                        except json.JSONDecodeError:
                            print(f"Error parsing JSON file: {file_name}")
                            continue

                # Update final results in the GUI thread
                self.frame.after(0, self._update_results, total_games, wins, total_elo_change, matching_replay_ids, card_wins, card_games)

        except Exception as e:
            self.frame.after(0, lambda: tk.messagebox.showerror("Error", f"An error occurred: {str(e)}"))
            print(e.with_traceback())

    def _update_progress(self, current, total):
        """Update progress bar and label from the worker thread"""
        if total > 0:
            progress = (current / total) * 100
            self.frame.after(0, lambda: self.progress_bar.configure(value=progress))
            self.frame.after(0, lambda: self.progress_label.configure(
                text=f"{current} / {total} ({progress:.1f}%)"
            ))

    def _update_results(self, total_games, wins, total_elo_change, matching_replay_ids, card_wins, card_games):
        """Update all results in the GUI - called from the main thread"""
        # Win rate
        if total_games > 0:
            win_rate = (wins / total_games) * 100
            self.win_rate_var.set(f"{win_rate:.1f}% ({wins}/{total_games})")
            avg_elo_change = total_elo_change / total_games
            self.elo_change_var.set(f"{avg_elo_change:.1f}")
        else:
            self.win_rate_var.set("No matching games found")
            
        # Update replay IDs
        self.replay_ids_text.delete('1.0', tk.END)
        self.replay_ids_text.insert('1.0', ", ".join(str(id) for id in matching_replay_ids))

        # Update card win rates
        card_win_rates = {}
        for card in card_games:
            if card not in card_wins:
                card_wins[card] = 0
            card_win_rates[card] = card_wins.get(card) / card_games.get(card)
            
        card_win_rates = dict(sorted(card_win_rates.items(), key=lambda c: c[1], reverse=True))
        
        self.card_win_rates_text.delete('1.0', tk.END)
        for card in card_win_rates:
            line = f"{card}\t{round(card_win_rates[card]*100,1)}%\t{card_games[card]}\n"
            self.card_win_rates_text.insert(tk.INSERT, line)