"""Scheduler dashboard tab showing run history, status, and configuration."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class SchedulerTab:
    """Dashboard tab for daily scraping job history and controls."""

    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.frame = ttk.Frame(parent)

        # Settings variables
        self.scheduler_enabled_var = tk.BooleanVar()
        self.scheduler_time_var = tk.StringVar()
        self.scheduler_game_count_var = tk.IntVar()

        self.create_widgets()
        self.load_settings()
        self.refresh()

    def create_widgets(self):
        # --- Settings section at top ---
        settings_frame = ttk.LabelFrame(self.frame, text="Schedule Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=(10, 5))

        # Row 1: Enable + Time + Game count
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill="x", pady=2)

        ttk.Checkbutton(
            row1, text="Enable daily scraping",
            variable=self.scheduler_enabled_var,
        ).pack(side="left")

        ttk.Label(row1, text="    Games:").pack(side="right")
        ttk.Spinbox(
            row1, from_=1, to=200,
            textvariable=self.scheduler_game_count_var, width=5,
        ).pack(side="right")

        ttk.Label(row1, text="    Run at:").pack(side="right")
        ttk.Entry(
            row1, textvariable=self.scheduler_time_var, width=6,
        ).pack(side="right")

        # Row 2: Save button + status
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill="x", pady=(5, 0))

        ttk.Button(row2, text="Save & Apply", command=self._save_settings).pack(side="left")

        self.settings_status_label = ttk.Label(row2, text="", foreground="gray")
        self.settings_status_label.pack(side="left", padx=(10, 0))

        # --- Status bar ---
        status_frame = ttk.LabelFrame(self.frame, text="Task Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)

        self.status_label = ttk.Label(status_frame, text="Checking...", font=("", 10))
        self.status_label.pack(fill="x")

        btn_frame = ttk.Frame(status_frame)
        btn_frame.pack(fill="x", pady=(8, 0))

        ttk.Button(btn_frame, text="Refresh", command=self.refresh).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Run Now", command=self._run_now).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="View Log", command=self._view_log).pack(side="left", padx=5)

        # --- History table ---
        history_frame = ttk.LabelFrame(self.frame, text="Run History", padding=10)
        history_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("date", "processed", "successes", "failures", "duration", "status")
        self.tree = ttk.Treeview(
            history_frame, columns=columns, show="headings", height=12,
        )

        self.tree.heading("date", text="Date")
        self.tree.heading("processed", text="Processed")
        self.tree.heading("successes", text="Successes")
        self.tree.heading("failures", text="Failures")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("status", text="Status")

        self.tree.column("date", width=160)
        self.tree.column("processed", width=80, anchor="center")
        self.tree.column("successes", width=80, anchor="center")
        self.tree.column("failures", width=80, anchor="center")
        self.tree.column("duration", width=80, anchor="center")
        self.tree.column("status", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Totals bar at bottom
        totals_frame = ttk.Frame(self.frame)
        totals_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.totals_label = ttk.Label(totals_frame, text="", foreground="gray")
        self.totals_label.pack(fill="x")

    def load_settings(self):
        scheduler_settings = self.config_manager.get_section("scheduler_settings")
        self.scheduler_enabled_var.set(scheduler_settings.get("enabled", False))
        self.scheduler_time_var.set(scheduler_settings.get("time", "03:00"))
        self.scheduler_game_count_var.set(scheduler_settings.get("game_count", 200))

    def _save_settings(self):
        enabled = self.scheduler_enabled_var.get()
        time_str = self.scheduler_time_var.get() or "03:00"
        game_count = self.scheduler_game_count_var.get() or 200

        self.config_manager.update_section("scheduler_settings", {
            "enabled": enabled,
            "time": time_str,
            "game_count": game_count,
        })
        self.config_manager.save_config()

        self.settings_status_label.config(text="Applying...", foreground="gray")

        import threading
        threading.Thread(
            target=self._apply_scheduler_task,
            args=(enabled, time_str),
            daemon=True,
        ).start()

    def _apply_scheduler_task(self, enabled, time_str):
        try:
            from scheduler.task_manager import (
                create_or_update_task, delete_task, get_exe_path, get_working_dir,
            )
            if enabled:
                exe_path = get_exe_path()
                working_dir = get_working_dir()
                if create_or_update_task(exe_path, working_dir, time_str):
                    self.frame.after(0, lambda: self.settings_status_label.config(
                        text="Saved. Task scheduled.", foreground="green",
                    ))
                else:
                    self.frame.after(0, lambda: self.settings_status_label.config(
                        text="Failed to create task.", foreground="red",
                    ))
            else:
                delete_task()
                self.frame.after(0, lambda: self.settings_status_label.config(
                    text="Saved. Task removed.", foreground="green",
                ))
        except Exception as e:
            self.frame.after(0, lambda: self.settings_status_label.config(
                text=f"Error: {e}", foreground="red",
            ))

        self.frame.after(100, self._refresh_status)

    def refresh(self):
        self._refresh_status()
        self._refresh_history()

    def _refresh_status(self):
        import threading

        def _query():
            try:
                from scheduler.task_manager import query_task
                info = query_task()
            except Exception:
                info = None

            def _update():
                if info:
                    next_run = info.get("next_run", "unknown")
                    last_run = info.get("last_run", "N/A")
                    if last_run and "1999" in last_run:
                        last_run = "Never"
                    self.status_label.config(
                        text=f"Task installed  |  Next run: {next_run}  |  Last run: {last_run}",
                        foreground="green",
                    )
                else:
                    if self.scheduler_enabled_var.get():
                        self.status_label.config(
                            text="Enabled but task not found. Click 'Save & Apply' to install.",
                            foreground="orange",
                        )
                    else:
                        self.status_label.config(
                            text="Not scheduled. Enable above and click 'Save & Apply'.",
                            foreground="gray",
                        )

            self.frame.after(0, _update)

        threading.Thread(target=_query, daemon=True).start()

    def _refresh_history(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            from scheduler.history import load_history
            history = load_history()
        except Exception:
            history = []

        total_processed = 0
        total_successes = 0
        total_failures = 0

        for entry in reversed(history):
            date_str = entry.get("date", "")
            try:
                dt = datetime.fromisoformat(date_str)
                date_display = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_display = date_str

            processed = entry.get("processed", 0)
            successes = entry.get("successes", 0)
            failures = entry.get("failures", 0)
            duration_s = entry.get("duration_seconds", 0)
            status = entry.get("status", "")

            if duration_s >= 3600:
                duration_display = f"{duration_s // 3600}h {(duration_s % 3600) // 60}m"
            elif duration_s >= 60:
                duration_display = f"{duration_s // 60}m {duration_s % 60}s"
            else:
                duration_display = f"{duration_s}s"

            self.tree.insert("", "end", values=(
                date_display, processed, successes, failures, duration_display, status,
            ))

            total_processed += processed
            total_successes += successes
            total_failures += failures

        if history:
            self.totals_label.config(
                text=f"Total: {len(history)} runs  |  "
                     f"{total_processed} processed  |  "
                     f"{total_successes} successes  |  "
                     f"{total_failures} failures",
            )
        else:
            self.totals_label.config(text="No run history yet.")

    def _run_now(self):
        if messagebox.askyesno("Run Now", "Start a scraping run now? This will run in the background."):
            import threading

            def run():
                try:
                    from scheduler.runner import run_scheduled_scraping
                    run_scheduled_scraping()
                except Exception as e:
                    print(f"Scheduled run error: {e}")
                finally:
                    self.frame.after(0, self.refresh)

            t = threading.Thread(target=run, daemon=True)
            t.start()
            self.status_label.config(text="Running now...", foreground="blue")

    def _view_log(self):
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            # __file__ is gui/tabs/scheduler_tab.py -> go up 3 levels to project root
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.join(base, "scheduler.log")

        if not os.path.exists(log_path):
            messagebox.showinfo("Log", "No scheduler log file found yet.")
            return

        try:
            os.startfile(log_path)
        except Exception:
            subprocess.Popen(["notepad", log_path])
