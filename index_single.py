#!/usr/bin/env python3
"""
Index a single BGA Terraforming Mars game (table page + gamereview).
Uses config.py for settings, same as index_top_players.py.

Usage:
    python index_single.py <table_id> <player_perspective>
"""

import argparse
import logging
import sys

import config
from bga_tm_scraper.scraper import TMScraper
from bga_tm_scraper.parser import Parser


def main():
    parser = argparse.ArgumentParser(description="Index a single BGA TM game.")
    parser.add_argument("table_id", help="BGA table ID")
    parser.add_argument("player_perspective", help="Player ID for perspective")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    scraper = TMScraper(
        chromedriver_path=config.CHROMEDRIVER_PATH,
        chrome_path=config.CHROME_PATH,
        request_delay=config.REQUEST_DELAY,
        headless=True,
        email=config.BGA_EMAIL,
        password=config.BGA_PASSWORD,
    )
    scraper.speed_settings = config.CURRENT_SPEED
    scraper.speed_profile = config.SPEED_PROFILE

    if not scraper.start_browser_and_login():
        print("Authentication failed.")
        sys.exit(1)

    try:
        result = scraper.scrape_table_only(
            args.table_id, args.player_perspective,
            save_raw=False, raw_data_dir=None
        )

        if not result:
            print("Failed.")
            sys.exit(1)

        print(f"\nResult for table {args.table_id}:")
        print(f"  Success: {result.get('success')}")
        print(f"  Game mode: {result.get('game_mode')}")
        print(f"  Version: {result.get('version')}")
        print(f"  Map: {result.get('map')}")

        elo_data = result.get('elo_data', {})
        if elo_data:
            print(f"  Players:")
            for name, elo in elo_data.items():
                print(f"    {name} ({elo.player_id}): pos={elo.position} arena={elo.arena_points}")

    finally:
        scraper.close_browser()


if __name__ == "__main__":
    main()
