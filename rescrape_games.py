#!/usr/bin/env python3
"""
Re-scrape games that are already in the registry and replace their stored game logs.

Used after a parser fix, for games whose stored log was parsed wrongly. One browser
session is used for the whole list. Uploads go to the production registry API.

The list is a JSON file: [{"table": 926358228, "perspective": 86296239, "scraped_by": "a@b.c"}, ...]
"scraped_by" is the contributor who scraped the game originally. StoreGameLog overwrites
ScrapedBy, so it is passed back to keep their credit; ScrapedAt becomes the time of upload.

Usage:
    python rescrape_games.py games.json
    python rescrape_games.py games.json --no-upload --limit 1
    python rescrape_games.py games.json --results results.jsonl   # games already in it are skipped
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

import config
from bga_tm_scraper.scraper import TMScraper
from bga_tm_scraper.parser import Parser
from gui.api_client import APIClient
from gui.version import BUILD_VERSION

RAW_DIR = "data/rescraped"
MAX_CONSECUTIVE_FAILURES = 3


def misfiled_card_plays(game_data):
    """Card plays filed under a player other than the one the log line names."""
    names = {p.player_name: str(pid) for pid, p in (game_data.players or {}).items()}
    problems = []
    for move in game_data.moves:
        if not move.card_played or move.action_type == "draft":
            continue
        for line in (move.description or "").split(" | "):
            for name, pid in names.items():
                if line == f"{name} plays card {move.card_played}" and str(move.player_id) != pid:
                    problems.append(move.move_number)
    return problems


def scrape_and_parse(scraper, tm_parser, table_id, perspective):
    """Returns (game_data, error). error is 'daily_limit' when BGA's replay limit is hit."""
    index_result = scraper.scrape_table_only(table_id, perspective, save_raw=True, raw_data_dir=RAW_DIR)
    if not index_result or not index_result.get("success"):
        return None, "table page failed"
    version_id = index_result.get("version")
    if not version_id:
        return None, "no version id"

    replay_result = scraper.scrape_replay_only_with_metadata(
        table_id=table_id, version_id=version_id, player_perspective=perspective,
        save_raw=True, raw_data_dir=RAW_DIR,
    )
    if not replay_result:
        return None, "replay page failed"
    if replay_result.get("daily_limit_reached") or replay_result.get("error") == "replay_limit_reached":
        return None, "daily_limit"
    replay_html = replay_result.get("html_content", "")
    if not replay_html:
        return None, "empty replay"

    game_metadata = None
    table_html = index_result.get("table_html", "")
    if table_html:
        game_metadata = tm_parser.parse_table_metadata(table_html)
    if not game_metadata:
        return None, "no table metadata"

    game_data = tm_parser.parse_complete_game(
        replay_html=replay_html, game_metadata=game_metadata,
        table_id=table_id, player_perspective=perspective,
    )
    if not game_data or not game_data.moves:
        return None, "parse failed"
    return game_data, None


def main():
    arg_parser = argparse.ArgumentParser(description="Re-scrape registered games and replace their stored logs.")
    arg_parser.add_argument("games", help="JSON file with the games to re-scrape")
    arg_parser.add_argument("--results", default=None, help="JSONL file for per-game results (default: <games>.results.jsonl)")
    arg_parser.add_argument("--no-upload", action="store_true", help="Scrape and parse only")
    arg_parser.add_argument("--limit", type=int, default=None, help="Stop after this many games")
    args = arg_parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    with open(args.games, encoding="utf-8-sig") as f:
        games = json.load(f)
    results_path = args.results or os.path.splitext(args.games)[0] + ".results.jsonl"

    done = set()
    if os.path.exists(results_path):
        with open(results_path, encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                if record.get("status") in ("uploaded", "parsed"):
                    done.add((str(record["table"]), str(record["perspective"])))
    todo = [g for g in games if (str(g["table"]), str(g["perspective"])) not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(games)} games in list, {len(done)} already done, {len(todo)} to do. Version {BUILD_VERSION}.")
    if not todo:
        return

    scraper = TMScraper(
        chromedriver_path=config.CHROMEDRIVER_PATH, chrome_path=config.CHROME_PATH,
        request_delay=config.REQUEST_DELAY, headless=True,
        email=config.BGA_EMAIL, password=config.BGA_PASSWORD,
    )
    scraper.speed_settings = config.CURRENT_SPEED
    scraper.speed_profile = config.SPEED_PROFILE
    if not scraper.start_browser_and_login():
        print("Authentication failed.")
        sys.exit(1)

    tm_parser = Parser()
    api = None if args.no_upload else APIClient(api_key=config.API_KEY, version=BUILD_VERSION)
    counts = {}
    consecutive_failures = 0

    try:
        for i, game in enumerate(todo, 1):
            table_id, perspective = str(game["table"]), str(game["perspective"])
            status, detail = "failed", ""
            try:
                game_data, error = scrape_and_parse(scraper, tm_parser, table_id, perspective)
                if error == "daily_limit":
                    print(f"[{i}/{len(todo)}] {table_id}: daily replay limit reached, stopping.")
                    break
                if error:
                    detail = error
                else:
                    misfiled = misfiled_card_plays(game_data)
                    if misfiled:
                        detail = f"card plays still misfiled at moves {misfiled[:5]}; not uploaded"
                    elif args.no_upload:
                        status = "parsed"
                    else:
                        payload = tm_parser._convert_game_data_to_api_format(game_data, table_id, perspective)
                        if payload.get("metadata") is None:
                            payload["metadata"] = {}
                        payload["metadata"]["scraper_version"] = BUILD_VERSION
                        if api.store_game_log(payload, scraped_by_email=game.get("scraped_by") or None):
                            status = "uploaded"
                        else:
                            detail = "upload failed"
                    if status != "failed":
                        detail = f"{len(game_data.moves)} moves"
            except Exception as e:  # keep going: one bad game must not end the run
                detail = f"{type(e).__name__}: {e}"

            counts[status] = counts.get(status, 0) + 1
            print(f"[{i}/{len(todo)}] {table_id} ({perspective}): {status} {detail}", flush=True)
            with open(results_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"table": table_id, "perspective": perspective, "status": status,
                                    "detail": detail, "at": datetime.now().isoformat(timespec="seconds")}) + "\n")

            consecutive_failures = consecutive_failures + 1 if status == "failed" else 0
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"{MAX_CONSECUTIVE_FAILURES} games failed in a row, stopping.")
                break
            if status == "failed" and not scraper.is_driver_alive():
                if not scraper.restart_browser():
                    print("Browser restart failed, stopping.")
                    break
            if config.REQUEST_DELAY > 0:
                time.sleep(config.REQUEST_DELAY)
    finally:
        scraper.close_browser()

    print("Done:", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "nothing processed")
    print(f"Results: {results_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
