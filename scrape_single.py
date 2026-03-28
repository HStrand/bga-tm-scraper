#!/usr/bin/env python3
"""
Scrape a single BGA Terraforming Mars game by table ID and player perspective.
Uses config.py for settings, same as index_top_players.py.

Two-phase flow:
  Phase 1: Index - scrape table page + gamereview to get metadata and version ID
  Phase 2: Scrape - use version ID to scrape the replay page and parse game data

Usage:
    python scrape_single.py <table_id> <player_perspective>

Example:
    python scrape_single.py 824655675 86296239
    python scrape_single.py 824655675 86296239 --output my_game.json
    python scrape_single.py 824655675 86296239 --no-upload
"""

import argparse
import logging
import sys
import os

import config
from bga_tm_scraper.scraper import TMScraper
from bga_tm_scraper.parser import Parser
from gui.api_client import APIClient


def main():
    parser = argparse.ArgumentParser(description="Scrape a single BGA TM game (index + replay).")
    parser.add_argument("table_id", help="BGA table ID")
    parser.add_argument("player_perspective", help="Player ID for replay perspective")
    parser.add_argument("-o", "--output", help="Output JSON path (default: data/sample files/game_<table>_<player>.json)")
    parser.add_argument("--no-upload", action="store_true", help="Skip uploading to API")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    output_path = args.output or f"data/sample files/game_{args.table_id}_{args.player_perspective}.json"

    print(f"Scraping game {args.table_id} from perspective {args.player_perspective}")

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

    tm_parser = Parser()
    api = None

    try:
        # Phase 1: Index (table + gamereview)
        print(f"\n[Phase 1] Indexing game metadata...")
        index_result = scraper.scrape_table_only(
            args.table_id, args.player_perspective,
            save_raw=True, raw_data_dir="data/sample files"
        )

        if not index_result or not index_result.get('success'):
            print("Failed to index game.")
            sys.exit(1)

        version_id = index_result.get('version')
        if not version_id:
            print("Failed to extract version ID.")
            sys.exit(1)

        table_html = index_result.get('table_html', '')
        game_metadata = None
        if table_html:
            game_metadata = tm_parser.parse_table_metadata(table_html)

        print(f"  Version: {version_id}")
        print(f"  Mode: {index_result.get('game_mode', 'Unknown')}")
        print(f"  Map: {index_result.get('map', 'Unknown')}")

        # Upload index data to API (required before submitting game log)
        if not args.no_upload:
            api_key = getattr(config, 'API_KEY', None)
            api_base_url = getattr(config, 'API_BASE_URL', "https://bga-tm-scraper-functions.azurewebsites.net/api")
            if api_key:
                api = APIClient(api_key=api_key, base_url=api_base_url)
                api.timeout = getattr(config, 'TIMEOUT', 60)

                elo_data = index_result.get('elo_data', {})
                players_list = []
                for pname, elo in elo_data.items():
                    players_list.append({
                        'player_name': elo.player_name or pname,
                        'player_id': elo.player_id,
                        'position': elo.position,
                        'arena_points': elo.arena_points,
                        'arena_points_change': elo.arena_points_change,
                        'game_rank': elo.game_rank,
                        'game_rank_change': elo.game_rank_change,
                    })

                game_api_data = {
                    'table_id': args.table_id,
                    'raw_datetime': index_result.get('game_date_info', {}).get('raw_datetime') if index_result.get('game_date_info') else None,
                    'parsed_datetime': index_result.get('game_date_info', {}).get('parsed_datetime') if index_result.get('game_date_info') else None,
                    'game_mode': index_result.get('game_mode'),
                    'version': version_id,
                    'player_perspective': args.player_perspective,
                    'scraped_at': index_result.get('scraped_at'),
                    'players': players_list,
                    'map': index_result.get('map'),
                    'prelude_on': index_result.get('prelude_on'),
                    'colonies_on': index_result.get('colonies_on'),
                    'corporate_era_on': index_result.get('corporate_era_on'),
                    'draft_on': index_result.get('draft_on'),
                    'beginners_corporations_on': index_result.get('beginners_corporations_on'),
                    'game_speed': index_result.get('game_speed'),
                }

                if api.update_single_game(game_api_data, indexed_by_email=config.BGA_EMAIL):
                    print(f"  Indexed game {args.table_id} in API")
                else:
                    print(f"  Failed to index game in API")

        # Phase 2: Scrape replay
        print(f"\n[Phase 2] Scraping replay...")
        replay_result = scraper.scrape_replay_only_with_metadata(
            table_id=args.table_id,
            version_id=version_id,
            player_perspective=args.player_perspective,
            save_raw=True,
            raw_data_dir="data/sample files",
        )

        if not replay_result:
            print("Failed to scrape replay.")
            sys.exit(1)

        if replay_result.get("daily_limit_reached") or replay_result.get("error") == "replay_limit_reached":
            print("Daily replay limit reached.")
            sys.exit(1)

        replay_html = replay_result.get("html_content", "")
        if not replay_html:
            print("No replay HTML content.")
            sys.exit(1)

        print(f"  Replay HTML: {len(replay_html)} bytes")

        # Build metadata from index result if table HTML parsing failed
        if not game_metadata:
            game_metadata = tm_parser.convert_assignment_to_game_metadata({
                "players": [
                    {"playerId": int(elo.player_id), "playerName": elo.player_name,
                     "position": elo.position, "arenaPoints": elo.arena_points,
                     "arenaPointsChange": elo.arena_points_change,
                     "elo": elo.game_rank, "eloChange": elo.game_rank_change}
                    for elo in index_result.get('elo_data', {}).values()
                    if elo and elo.player_id
                ],
                "map": index_result.get('map'),
                "preludeOn": index_result.get('prelude_on'),
                "coloniesOn": index_result.get('colonies_on'),
                "corporateEraOn": index_result.get('corporate_era_on'),
                "draftOn": index_result.get('draft_on'),
                "beginnersCorporationsOn": index_result.get('beginners_corporations_on'),
                "gameSpeed": index_result.get('game_speed'),
                "gameMode": index_result.get('game_mode'),
                "playedAt": index_result.get('game_date_info', {}).get('parsed_datetime') if index_result.get('game_date_info') else None,
            })

        # Parse
        print(f"\nParsing game data...")
        game_data = tm_parser.parse_complete_game(
            replay_html=replay_html,
            game_metadata=game_metadata,
            table_id=args.table_id,
            player_perspective=args.player_perspective,
        )

        if not game_data:
            print("Parsing failed.")
            sys.exit(1)

        # Export locally
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        tm_parser.export_to_json(game_data, output_path, player_perspective=None)
        print(f"\nWrote {output_path}")

        # Summary
        print(f"\n  Winner: {game_data.winner}")
        print(f"  Conceded: {game_data.conceded}")
        print(f"  Generations: {game_data.generations}")
        print(f"  Moves: {len(game_data.moves)}")
        print(f"  Map: {game_data.map}")
        for pid, player in (game_data.players or {}).items():
            print(f"  {player.player_name} ({pid}): {player.corporation}, {player.final_vp} VP, color={player.color}")

        # Upload game log to API
        if not args.no_upload and api:
            print(f"\nUploading game log to API...")
            payload = tm_parser._convert_game_data_to_api_format(game_data, args.table_id, args.player_perspective)
            # Add scraper version to metadata
            from gui.version import BUILD_VERSION
            if payload.get("metadata") is None:
                payload["metadata"] = {}
            payload["metadata"]["scraper_version"] = BUILD_VERSION
            if api.store_game_log(payload, scraped_by_email=config.BGA_EMAIL):
                print(f"Uploaded game {args.table_id}")
            else:
                print(f"Failed to upload game {args.table_id}")

    finally:
        scraper.close_browser()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
