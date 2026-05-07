#!/usr/bin/env python3
"""
BGA TM Scraper - Desktop GUI Application
A user-friendly desktop interface for the Terraforming Mars scraper
"""

import argparse
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from pathlib import Path

# Python 3.14 + PyInstaller windowed builds bind stdout/stderr to the parent's
# cp1252 stream on Windows; emoji in print() then raises UnicodeEncodeError and
# breaks --scheduled-run. Force UTF-8 with replacement so prints can't crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream is not None:
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add the current directory to Python path to import our modules
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def main():
    """Main entry point for the GUI application"""
    parser = argparse.ArgumentParser(description="BGA TM Scraper")
    parser.add_argument(
        "--scheduled-run", action="store_true",
        help="Run headless scraping (used by Task Scheduler)",
    )
    args = parser.parse_args()

    if args.scheduled_run:
        from scheduler.runner import run_scheduled_scraping
        sys.exit(run_scheduled_scraping())

    try:
        from gui.main_window import MainWindow

        # Create the main application window
        root = tk.Tk()
        app = MainWindow(root)

        # Start the GUI event loop
        root.mainloop()

    except Exception as e:
        # Show error dialog if something goes wrong during startup
        messagebox.showerror(
            "Startup Error",
            f"Failed to start BGA TM Scraper:\n\n{str(e)}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
