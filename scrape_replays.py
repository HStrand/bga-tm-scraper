#!/usr/bin/env python3
"""
Simple CLI script to perform replay scraping assignments.

- Requests a new 'replayscraping' assignment (default 200 games; configurable with --count).
- Uses config.py for BGA credentials, Chrome/Chromedriver paths, API key, and request delay.
- Starts a headless Chrome session, logs into BGA, scrapes replay pages using assignment metadata,
  parses them into structured data, and uploads via the API's StoreGameLog endpoint.
- Stops immediately if the daily replay limit is reached.

Intended for automation (e.g., daily scheduler/cron/Task Scheduler).
"""

import argparse
import logging
import sys
import time
from typing import Any, Dict, Optional

# Try to import local config; fall back to example with a clear message if missing
try:
    import config  # type: ignore
except ImportError as e:
    print("ERROR: config.py not found. Copy config.example.py to config.py and fill in your values.")
    sys.exit(1)

from gui.api_client import APIClient

from bga_tm_scraper.scraper import TMScraper
from bga_tm_scraper.parser import Parser

# Optional version string as used by GUI; if missing, proceed without it
try:
    from gui.version import BUILD_VERSION as GUI_BUILD_VERSION
except Exception:
    GUI_BUILD_VERSION = None


def build_assignment_metadata(game: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the assignment metadata structure expected by Parser.convert_assignment_to_game_metadata
    from a single 'game' entry in the assignment.
    """
    return {
        "gameMode": game.get("gameMode", "Arena mode"),
        "versionId": game.get("versionId", ""),
        "players": game.get("players", []),  # array of { playerId, playerName, position, arenaPoints, arenaPointsChange, elo, eloChange }
        "map": game.get("map"),
        "preludeOn": game.get("preludeOn"),
        "coloniesOn": game.get("coloniesOn"),
        "corporateEraOn": game.get("corporateEraOn"),
        "draftOn": game.get("draftOn"),
        "beginnersCorporationsOn": game.get("beginnersCorporationsOn"),
        "gameSpeed": game.get("gameSpeed"),
        "playedAt": game.get("playedAt"),
    }


def request_assignment(api: APIClient, email: str, count: int) -> Optional[Dict[str, Any]]:
    """
    Request a new assignment from the API.
    """
    return api.get_next_assignment(email, count)


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay scraping CLI for BGA Terraforming Mars."
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=200,
        help="Number of games to request (max 200). Default: 200",
    )
    return parser.parse_args()


def scraping_loop(api, scraper, parser, games, per_game_delay, email, logger):
    """
    Process a list of replay scraping assignments.
    Returns dict with keys: processed, successes, failures, limit_reached.
    """
    successes = 0
    failures = 0
    processed = 0
    limit_reached = False

    for idx, game in enumerate(games, start=1):
        table_id = str(game.get("tableId", ""))
        version_id = str(game.get("versionId", ""))
        player_perspective = str(game.get("playerPerspective", ""))

        if not (table_id and version_id and player_perspective):
            logger.warning(
                f"Skipping game #{idx}: missing tableId/versionId/playerPerspective"
            )
            failures += 1
            continue

        logger.info(f"[{idx}/{len(games)}] Processing game {table_id} (version {version_id}) ...")

        assignment_meta = build_assignment_metadata(game)

        try:
            replay_result = scraper.scrape_replay_only_with_metadata(
                table_id=table_id,
                version_id=version_id,
                player_perspective=player_perspective,
                save_raw=False,
                raw_data_dir=None,
            )
        except Exception as e:
            logger.error(f"Scrape failed for table {table_id}: {e}")
            failures += 1
            processed += 1
            if per_game_delay and per_game_delay > 0:
                time.sleep(per_game_delay)
            continue

        # Daily limit detection
        if replay_result and (
            replay_result.get("daily_limit_reached")
            or replay_result.get("limit_reached")
            or replay_result.get("error") == "replay_limit_reached"
        ):
            logger.info("Daily replay limit reached - stopping.")
            limit_reached = True
            break

        if replay_result and (replay_result.get("replay_deleted") or replay_result.get("error") == "replay_deleted"):
            logger.warning(f"Replay permanently deleted for table {table_id}")
            try:
                api.report_game_deleted(table_id, player_perspective)
            except Exception as e:
                logger.error(f"Failed to report deleted game {table_id}: {e}")
            processed += 1
            if per_game_delay and per_game_delay > 0:
                time.sleep(per_game_delay)
            continue

        if not replay_result:
            logger.warning(f"Failed to scrape replay for table {table_id}")
            failures += 1
            processed += 1
            if per_game_delay and per_game_delay > 0:
                time.sleep(per_game_delay)
            continue

        if "html_content" in replay_result:
            try:
                gm = parser.convert_assignment_to_game_metadata(assignment_meta)
                game_obj = parser.parse_complete_game(
                    replay_html=replay_result["html_content"],
                    game_metadata=gm,
                    table_id=table_id,
                    player_perspective=player_perspective,
                )
                payload = parser._convert_game_data_to_api_format(game_obj, table_id, player_perspective)
            except Exception as e:
                logger.error(f"Parsing failed for table {table_id}: {e}")
                failures += 1
                processed += 1
                if per_game_delay and per_game_delay > 0:
                    time.sleep(per_game_delay)
                continue
        else:
            payload = replay_result

        try:
            if api.store_game_log(payload, scraped_by_email=email):
                successes += 1
                logger.info(f"  Uploaded logs for game {table_id}")
            else:
                failures += 1
                logger.warning(f"  Failed to upload logs for game {table_id}")
        except Exception as e:
            logger.error(f"Upload failed for table {table_id}: {e}")
            failures += 1

        processed += 1

        if per_game_delay and per_game_delay > 0:
            time.sleep(per_game_delay)

    return {
        "processed": processed,
        "successes": successes,
        "failures": failures,
        "limit_reached": limit_reached,
    }


def main():
    args = parse_args()
    configure_logging()
    logger = logging.getLogger("scrape_replays")

    # Validate required config values
    missing = []
    if not getattr(config, "API_KEY", None):
        missing.append("API_KEY")
    if not getattr(config, "BGA_EMAIL", None):
        missing.append("BGA_EMAIL")
    if not getattr(config, "BGA_PASSWORD", None):
        missing.append("BGA_PASSWORD")

    if missing:
        print("ERROR: Missing required values in config.py:")
        for k in missing:
            print(f" - {k}")
        sys.exit(1)

    # Prepare API client
    api = APIClient(
        api_key=config.API_KEY,
        base_url=getattr(
            config, "API_BASE_URL", "https://bga-tm-scraper-functions.azurewebsites.net/api"
            # config, "API_BASE_URL", "http://localhost:7184/api"
        ),
        version=GUI_BUILD_VERSION,
    )
    # Allow customizing request timeout via config if present
    api.timeout = getattr(config, "TIMEOUT", 60)

    # Cap the count at 200
    requested_count = max(1, min(int(args.count or 200), 200))
    logger.info(f"Requesting new assignment for {config.BGA_EMAIL} (count={requested_count})")

    assignment = request_assignment(api, config.BGA_EMAIL, requested_count)
    if not assignment:
        print("No assignment available (API returned no data).")
        sys.exit(0)

    assignment_type = str(assignment.get("assignmentType", "")).lower()
    if assignment_type != "replayscraping":
        print(f"Assignment type '{assignment.get('assignmentType')}' not supported by this CLI.")
        sys.exit(0)

    games = assignment.get("games", [])
    if not games:
        print("Assignment contains no games.")
        sys.exit(0)

    logger.info(f"Received replay scraping assignment with {len(games)} games")

    # Prepare scraper and parser
    headless = True
    per_game_delay = getattr(config, "REQUEST_DELAY", 0.0)

    scraper = TMScraper(
        chromedriver_path=getattr(config, "CHROMEDRIVER_PATH", None),
        chrome_path=getattr(config, "CHROME_PATH", None),
        request_delay=per_game_delay,
        headless=headless,
        email=config.BGA_EMAIL,
        password=config.BGA_PASSWORD,
    )

    if not scraper.start_browser_and_login():
        print("Authentication failed. Verify your BGA credentials and Chromedriver/Chrome settings in config.py.")
        sys.exit(1)

    parser = Parser()

    try:
        result = scraping_loop(
            api=api,
            scraper=scraper,
            parser=parser,
            games=games,
            per_game_delay=per_game_delay,
            email=config.BGA_EMAIL,
            logger=logger,
        )

        # Summary
        print("")
        print("Replay scraping summary")
        print("----------------------")
        print(f"Processed:  {result['processed']}")
        print(f"Successful: {result['successes']}")
        print(f"Failed:     {result['failures']}")

    finally:
        # Always close the browser
        try:
            scraper.close_browser()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
