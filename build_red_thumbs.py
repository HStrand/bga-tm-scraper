#!/usr/bin/env python3
"""
Build script for BGA Red Thumbs scraper executable.
"""

import os
import sys
import subprocess


def main():
    print("=" * 50)
    print("BGA Red Thumbs - Build Script")
    print("=" * 50)

    spec_file = "scrape_red_thumbs.spec"

    if not os.path.exists(spec_file):
        print(f"Error: {spec_file} not found. Run from the project root.")
        sys.exit(1)

    print(f"Running PyInstaller with {spec_file}...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean",
             "--distpath", "red_thumbs_dist", spec_file],
            check=True, capture_output=True, text=True,
        )
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed (exit code {e.returncode})")
        if e.stderr:
            print(e.stderr)
        if e.stdout:
            print(e.stdout)
        sys.exit(1)

    print("=" * 50)
    print("Build completed successfully!")
    print("Executable: red_thumbs_dist/BGA Red Thumbs.exe")
    print("Place a config.json next to the exe before running.")
    print("=" * 50)


if __name__ == "__main__":
    main()
