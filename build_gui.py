#!/usr/bin/env python3
"""
Build script for BGA TM Scraper GUI
Generates version file and builds executable with PyInstaller
"""

import os
import sys
import subprocess
from datetime import datetime, timezone

def generate_version_file():
    """Generate version.py file with current UTC build time"""
    # Get current UTC time
    utc_now = datetime.now(timezone.utc)
    version_string = utc_now.strftime("v%Y.%m.%d.%H%M")
    
    # Create version file content
    version_content = f'''"""
Auto-generated version file
Generated at build time with UTC timestamp
"""

BUILD_VERSION = "{version_string}"
BUILD_TIME_UTC = "{utc_now.isoformat()}"
'''
    
    # Write version file
    version_path = os.path.join("gui", "version.py")
    with open(version_path, "w", encoding="utf-8") as f:
        f.write(version_content)
    
    print(f"Generated version file: {version_path}")
    print(f"Build version: {version_string}")
    return version_string

def run_pyinstaller():
    """Run PyInstaller with the spec file"""
    spec_file = "gui_main.spec"
    
    if not os.path.exists(spec_file):
        print(f"Error: {spec_file} not found!")
        return False
    
    print(f"Running PyInstaller with {spec_file}...")
    
    try:
        # Run PyInstaller
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--clean",  # Clean PyInstaller cache
            spec_file
        ], check=True, capture_output=True, text=True)
        
        print("PyInstaller completed successfully!")
        print("Build output:")
        if result.stdout:
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed with return code {e.returncode}")
        print("Error output:")
        if e.stderr:
            print(e.stderr)
        if e.stdout:
            print(e.stdout)
        return False

def main():
    """Main build process"""
    print("=" * 50)
    print("BGA TM Scraper GUI Build Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("gui_main.py"):
        print("Error: gui_main.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Generate version file
    try:
        version = generate_version_file()
    except Exception as e:
        print(f"Error generating version file: {e}")
        sys.exit(1)
    
    # Run PyInstaller
    if not run_pyinstaller():
        print("Build failed!")
        sys.exit(1)
    
    print("=" * 50)
    print(f"Build completed successfully!")
    print(f"Version: {version}")
    print("Executable location: dist/BGA TM Scraper.exe")
    print("=" * 50)

if __name__ == "__main__":
    main()
