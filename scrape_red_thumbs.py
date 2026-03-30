#!/usr/bin/env python3
"""
Scrape red thumbs (given and received) from Board Game Arena.

Logs into BGA, fetches red thumb player IDs from the welcome page,
resolves each player ID to a username via their profile page,
and prints a complete list with profile links.
"""

import json
import logging
import os
import re
import sys
import time

import requests

from bga_tm_scraper.bga_session import BGASession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

PROFILE_URL = "https://boardgamearena.com/player?id={player_id}"


def build_requests_session(bga_session: BGASession) -> requests.Session:
    """Copy authenticated cookies from the browser into a requests.Session."""
    session = requests.Session()
    if bga_session.driver:
        for cookie in bga_session.driver.get_cookies():
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", ".boardgamearena.com"),
            )
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    return session


def extract_red_thumbs(page_source: str) -> dict:
    """
    Extract red_thumbs_given and red_thumbs_taken from the welcome page source.
    BGA embeds these as JS objects in the page.
    """
    # Look for the JSON-like structures in the page source
    given = {}
    taken = {}

    # Try to find red_thumbs_given and red_thumbs_taken in the page source
    # They appear as properties in a JS object, e.g. "red_thumbs_given": {"12345": "1", ...}
    given_match = re.search(r'"red_thumbs_given"\s*:\s*(\{[^}]*\})', page_source)
    taken_match = re.search(r'"red_thumbs_taken"\s*:\s*(\{[^}]*\})', page_source)

    if given_match:
        try:
            given = json.loads(given_match.group(1))
        except json.JSONDecodeError:
            logger.warning("Failed to parse red_thumbs_given JSON")

    if taken_match:
        try:
            taken = json.loads(taken_match.group(1))
        except json.JSONDecodeError:
            logger.warning("Failed to parse red_thumbs_taken JSON")

    return {"given": given, "taken": taken}


def resolve_username(session: requests.Session, player_id: str) -> str:
    """Fetch a player's profile page and extract their username."""
    url = PROFILE_URL.format(player_id=player_id)
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()

        # Extract from <span id="real_player_name">Username</span>
        name_match = re.search(r'<span\s+id="real_player_name">([^<]+)</span>', resp.text)
        if name_match:
            return name_match.group(1)

    except Exception as e:
        logger.warning(f"Failed to resolve username for player {player_id}: {e}")

    return f"Unknown ({player_id})"


def load_config() -> dict:
    """Load configuration from config.json next to the executable/script."""
    # When frozen by PyInstaller, sys._MEIPASS is the temp extraction dir,
    # but we want the directory where the .exe actually lives.
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    config_path = os.path.join(base_dir, "config.json")

    if not os.path.exists(config_path):
        print(f"ERROR: config.json not found at {config_path}")
        print("Create a config.json file next to the executable with this format:")
        print(json.dumps({
            "bga_email": "your_email@example.com",
            "bga_password": "your_password",
        }, indent=2))
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    if not cfg.get("bga_email") or not cfg.get("bga_password"):
        print("ERROR: config.json must contain 'bga_email' and 'bga_password'.")
        sys.exit(1)

    return cfg


def main():
    cfg = load_config()

    logger.info("Logging in to Board Game Arena...")
    bga = BGASession(
        email=cfg["bga_email"],
        password=cfg["bga_password"],
        chromedriver_path=None,
        headless=True,
    )

    if not bga.login():
        logger.error("Login failed.")
        sys.exit(1)

    logger.info("Login successful. Fetching welcome page...")

    # Navigate to the welcome page with the browser to get the full JS-rendered content
    bga.driver.get("https://boardgamearena.com/welcome")
    time.sleep(3)  # Let page fully load

    page_source = bga.driver.page_source
    thumbs = extract_red_thumbs(page_source)

    given_ids = list(thumbs["given"].keys())
    taken_ids = list(thumbs["taken"].keys())

    logger.info(f"Found {len(given_ids)} red thumbs given, {len(taken_ids)} red thumbs received.")

    if not given_ids and not taken_ids:
        logger.warning("No red thumbs found. The page structure may have changed.")
        bga.driver.quit()
        sys.exit(0)

    # Build a requests session for faster profile lookups
    http_session = build_requests_session(bga)

    # Resolve all unique player IDs
    all_ids = set(given_ids + taken_ids)
    usernames = {}
    for i, pid in enumerate(all_ids, 1):
        logger.info(f"Resolving player {i}/{len(all_ids)}: {pid}")
        usernames[pid] = resolve_username(http_session, pid)
        time.sleep(1)  # Be polite

    # Print results
    print("\n" + "=" * 70)
    print("RED THUMBS REPORT")
    print("=" * 70)

    print(f"\n--- Red Thumbs Given ({len(given_ids)}) ---")
    for pid in given_ids:
        profile_url = PROFILE_URL.format(player_id=pid)
        print(f"  {usernames.get(pid, pid):30s}  {profile_url}")

    print(f"\n--- Red Thumbs Received ({len(taken_ids)}) ---")
    for pid in taken_ids:
        profile_url = PROFILE_URL.format(player_id=pid)
        print(f"  {usernames.get(pid, pid):30s}  {profile_url}")

    print("\n" + "=" * 70)

    bga.driver.quit()
    logger.info("Done.")

    if getattr(sys, "frozen", False):
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
