"""Headless scraping entry point for scheduled runs."""

import logging
import os
import sys
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from gui.components.config_manager import ConfigManager
from gui.api_client import APIClient
from bga_tm_scraper.scraper import TMScraper
from bga_tm_scraper.parser import Parser
from scrape_replays import scraping_loop, build_assignment_metadata, request_assignment
from scheduler.history import append_run, load_history

try:
    from gui.version import BUILD_VERSION
except Exception:
    BUILD_VERSION = None


def _get_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _setup_logging(base_dir: str) -> logging.Logger:
    log_path = os.path.join(base_dir, "scheduler.log")
    logger = logging.getLogger("scheduler")
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)

    # Also log to console (visible when running manually)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(console)

    # Suppress noisy libraries
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger


def run_scheduled_scraping() -> int:
    """
    Run a headless scraping session using config.json settings.
    Returns exit code: 0 = success, 1 = error.
    """
    base_dir = _get_base_dir()
    logger = _setup_logging(base_dir)
    logger.info("=" * 60)
    logger.info(f"Scheduled scraping run starting (build={BUILD_VERSION}, pid={os.getpid()})")
    logger.info(f"Base dir: {base_dir}")
    logger.info(f"Current time (UTC): {datetime.now(timezone.utc).isoformat()}")

    start_time = time.time()

    # Load config
    config_path = os.path.join(base_dir, "config.json")
    config_manager = ConfigManager(config_path)

    email, password, display_name = config_manager.get_bga_credentials()
    if not email or not password:
        logger.error("BGA credentials not configured. Aborting.")
        return 1

    api_settings = config_manager.get_section("api_settings")
    api_key = api_settings.get("api_key", "")
    if not api_key:
        logger.error("API key not configured. Aborting.")
        return 1

    scheduler_settings = config_manager.get_section("scheduler_settings")
    configured_count = int(scheduler_settings.get("game_count", 200))
    game_count = min(max(configured_count, 1), 200)
    scheduled_time = scheduler_settings.get("time", "?")
    logger.info(
        f"Scheduler settings: time={scheduled_time}, "
        f"game_count={configured_count} (clamped to {game_count})"
    )

    browser_settings = config_manager.get_section("browser_settings")
    scraping_settings = config_manager.get_section("scraping_settings")
    per_game_delay = scraping_settings.get("request_delay", 1.0)

    # Skip if a successful run already occurred in the last 24 hours
    # (hourly task repetition means we retry until one run lands).
    history = load_history()
    logger.info(f"Loaded {len(history)} run(s) from history")
    last_good = None
    for entry in reversed(history):
        status = entry.get("status")
        if status not in ("success", "partial", "limit_reached"):
            continue
        try:
            entry_time = datetime.fromisoformat(entry["date"])
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            hours_ago = (datetime.now(timezone.utc) - entry_time).total_seconds() / 3600
        except (ValueError, TypeError, KeyError):
            continue
        last_good = (entry, hours_ago)
        break

    if last_good:
        entry, hours_ago = last_good
        logger.info(
            f"Last completed run: status={entry.get('status')}, "
            f"at={entry.get('date')} ({hours_ago:.1f}h ago), "
            f"processed={entry.get('processed')}, successes={entry.get('successes')}, "
            f"failures={entry.get('failures')}"
        )
        if hours_ago < 24:
            logger.info(f"Within 24h window, skipping this run.")
            return 0
        logger.info("Over 24h since last run, proceeding.")
    else:
        logger.info("No prior completed run in history, proceeding.")

    # Check daily limit
    limit_hit_at = config_manager.get_replay_limit_hit_at()
    if limit_hit_at:
        try:
            hit_time = datetime.fromisoformat(limit_hit_at)
            hours_ago = (datetime.now(timezone.utc) - hit_time.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            logger.info(f"replay_limit_hit_at={limit_hit_at} ({hours_ago:.1f}h ago)")
            if hours_ago < 24:
                logger.info(f"Daily limit was hit {hours_ago:.1f} hours ago, skipping run.")
                return 0
        except (ValueError, TypeError):
            logger.warning(f"Could not parse replay_limit_hit_at={limit_hit_at!r}")
    else:
        logger.info("No prior daily-limit marker set.")

    # Build API client
    api = APIClient(
        api_key=api_key,
        base_url=api_settings.get("base_url", "https://bga-tm-scraper-functions.azurewebsites.net/api"),
        version=BUILD_VERSION,
    )
    api.timeout = api_settings.get("timeout", 60)

    # Fetch assignment
    logger.info(f"Requesting assignment for {email} (count={game_count})")
    assignment = request_assignment(api, email, game_count)
    if not assignment:
        logger.info("No assignment available.")
        return 0

    assignment_type = str(assignment.get("assignmentType", "")).lower()
    if assignment_type != "replayscraping":
        logger.info(f"Assignment type '{assignment.get('assignmentType')}' not supported.")
        return 0

    games = assignment.get("games", [])
    if not games:
        logger.info("Assignment contains no games.")
        return 0

    logger.info(f"Received {len(games)} games to scrape")

    # Build scraper
    scraper = TMScraper(
        chromedriver_path=browser_settings.get("chromedriver_path") or None,
        chrome_path=browser_settings.get("chrome_path") or None,
        request_delay=per_game_delay,
        headless=True,
        email=email,
        password=password,
    )

    if not scraper.start_browser_and_login():
        logger.error("Authentication failed. Check BGA credentials and browser settings.")
        return 1

    parser = Parser()

    try:
        result = scraping_loop(
            api=api,
            scraper=scraper,
            parser=parser,
            games=games,
            per_game_delay=per_game_delay,
            email=email,
            logger=logger,
        )
    finally:
        try:
            scraper.close_browser()
        except Exception:
            pass

    duration = time.time() - start_time

    # Record to history
    status = "success"
    if result["limit_reached"]:
        status = "limit_reached"
        config_manager.set_replay_limit_hit_at(datetime.now(timezone.utc).isoformat())
    elif result["failures"] > 0 and result["successes"] == 0:
        status = "error"
    elif result["failures"] > 0:
        status = "partial"

    append_run({
        "date": datetime.now(timezone.utc).isoformat(),
        "processed": result["processed"],
        "successes": result["successes"],
        "failures": result["failures"],
        "limit_reached": result["limit_reached"],
        "duration_seconds": round(duration),
        "status": status,
    })

    logger.info(
        f"Run complete: {result['processed']} processed, "
        f"{result['successes']} success, {result['failures']} failed, "
        f"duration {round(duration)}s"
    )

    return 0 if result["failures"] == 0 or result["successes"] > 0 else 1
