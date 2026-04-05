#!/usr/bin/env python3
"""
FastAPI web service for BGA Terraforming Mars scraping.

Maintains a persistent Chrome browser session and exposes HTTP endpoints
to scrape games on demand. Designed for deployment on an Azure VM.

Usage:
    python web_service.py
    uvicorn web_service:app --host 0.0.0.0 --port 8000
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from bga_tm_scraper.scraper import TMScraper
from bga_tm_scraper.parser import Parser
from gui.api_client import APIClient
from gui.version import BUILD_VERSION

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger("web_service")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
RESTART_AFTER_N_SCRAPES = 50
LOCK_TIMEOUT_SECONDS = 300

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ScrapeRequest(BaseModel):
    tableId: str
    playerPerspective: str


class ScrapeResponse(BaseModel):
    success: bool
    tableId: str
    playerPerspective: str
    message: str
    versionId: Optional[str] = None
    gameMode: Optional[str] = None
    map: Optional[str] = None
    generations: Optional[int] = None
    winner: Optional[str] = None
    conceded: Optional[bool] = None
    moves: Optional[int] = None
    indexUploaded: bool = False
    gameLogUploaded: bool = False
    durationSeconds: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    browserAlive: bool
    authenticated: bool
    gamesProcessed: int
    uptime: float
    lastScrapeAt: Optional[str] = None
    dailyLimitReached: bool = False


# ---------------------------------------------------------------------------
# Scrape Orchestrator
# ---------------------------------------------------------------------------

class ScrapeOrchestrator:
    def __init__(self):
        self.scraper: Optional[TMScraper] = None
        self.parser = Parser()
        self.api = APIClient(
            api_key=config.API_KEY,
            base_url=getattr(config, "API_BASE_URL", "https://bga-tm-scraper-functions.azurewebsites.net/api"),
            version=BUILD_VERSION,
        )
        self.api.timeout = getattr(config, "TIMEOUT", 60)

        self.browser_alive = False
        self.authenticated = False
        self.games_processed = 0
        self.start_time = time.time()
        self.last_scrape_at: Optional[str] = None
        self.daily_limit_reached = False

    def start(self) -> bool:
        logger.info("Starting browser and logging in...")
        self.scraper = TMScraper(
            chromedriver_path=config.CHROMEDRIVER_PATH,
            chrome_path=config.CHROME_PATH,
            request_delay=config.REQUEST_DELAY,
            headless=True,
            email=config.BGA_EMAIL,
            password=config.BGA_PASSWORD,
        )
        self.scraper.speed_settings = config.CURRENT_SPEED
        self.scraper.speed_profile = config.SPEED_PROFILE

        success = self.scraper.start_browser_and_login()
        self.browser_alive = success
        self.authenticated = success
        if success:
            logger.info("Browser started and authenticated")
        else:
            logger.error("Failed to start browser or authenticate")
        return success

    def stop(self):
        logger.info("Stopping browser...")
        if self.scraper:
            try:
                self.scraper.close_browser()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
        self.browser_alive = False
        self.authenticated = False

    def restart_browser(self) -> bool:
        logger.info("Restarting browser...")
        self.stop()
        return self.start()

    def health_status(self) -> HealthResponse:
        return HealthResponse(
            status="healthy" if self.browser_alive and self.authenticated else "unhealthy",
            browserAlive=self.browser_alive,
            authenticated=self.authenticated,
            gamesProcessed=self.games_processed,
            uptime=time.time() - self.start_time,
            lastScrapeAt=self.last_scrape_at,
            dailyLimitReached=self.daily_limit_reached,
        )

    def scrape_and_upload(self, table_id: str, player_perspective: str) -> ScrapeResponse:
        start = time.time()

        if not self.browser_alive or not self.scraper:
            return ScrapeResponse(
                success=False, tableId=table_id, playerPerspective=player_perspective,
                message="Browser not started",
            )

        # Auto-restart browser after N scrapes
        if self.games_processed > 0 and self.games_processed % RESTART_AFTER_N_SCRAPES == 0:
            logger.info(f"Auto-restarting browser after {self.games_processed} scrapes")
            if not self.restart_browser():
                return ScrapeResponse(
                    success=False, tableId=table_id, playerPerspective=player_perspective,
                    message="Browser restart failed",
                )

        try:
            # Phase 1: Index (table + gamereview)
            logger.info(f"[{table_id}] Phase 1: Indexing...")
            index_result = self.scraper.scrape_table_only(
                table_id, player_perspective, save_raw=False, raw_data_dir=None
            )

            if not index_result or not index_result.get("success"):
                return ScrapeResponse(
                    success=False, tableId=table_id, playerPerspective=player_perspective,
                    message="Failed to scrape table page",
                )

            version_id = index_result.get("version")
            if not version_id:
                return ScrapeResponse(
                    success=False, tableId=table_id, playerPerspective=player_perspective,
                    message="Failed to extract version ID",
                )

            table_html = index_result.get("table_html", "")
            game_metadata = None
            if table_html:
                game_metadata = self.parser.parse_table_metadata(table_html)

            game_mode = index_result.get("game_mode", "Unknown")
            map_name = index_result.get("map", "Unknown")
            logger.info(f"[{table_id}] Indexed: version={version_id}, mode={game_mode}, map={map_name}")

            # Upload index to API
            index_uploaded = False
            elo_data = index_result.get("elo_data", {})
            players_list = []
            for pname, elo in elo_data.items():
                players_list.append({
                    "player_name": elo.player_name or pname,
                    "player_id": elo.player_id,
                    "position": elo.position,
                    "arena_points": elo.arena_points,
                    "arena_points_change": elo.arena_points_change,
                    "game_rank": elo.game_rank,
                    "game_rank_change": elo.game_rank_change,
                })

            game_api_data = {
                "table_id": table_id,
                "raw_datetime": index_result.get("game_date_info", {}).get("raw_datetime") if index_result.get("game_date_info") else None,
                "parsed_datetime": index_result.get("game_date_info", {}).get("parsed_datetime") if index_result.get("game_date_info") else None,
                "game_mode": game_mode,
                "version": version_id,
                "player_perspective": player_perspective,
                "scraped_at": index_result.get("scraped_at"),
                "players": players_list,
                "map": map_name,
                "prelude_on": index_result.get("prelude_on"),
                "colonies_on": index_result.get("colonies_on"),
                "corporate_era_on": index_result.get("corporate_era_on"),
                "draft_on": index_result.get("draft_on"),
                "beginners_corporations_on": index_result.get("beginners_corporations_on"),
                "game_speed": index_result.get("game_speed"),
            }

            if self.api.update_single_game(game_api_data, indexed_by_email=config.BGA_EMAIL):
                index_uploaded = True
                logger.info(f"[{table_id}] Index uploaded to API")
            else:
                logger.warning(f"[{table_id}] Failed to upload index to API")

            # Phase 2: Scrape replay
            logger.info(f"[{table_id}] Phase 2: Scraping replay...")
            replay_result = self.scraper.scrape_replay_only_with_metadata(
                table_id=table_id,
                version_id=version_id,
                player_perspective=player_perspective,
                save_raw=False,
                raw_data_dir=None,
            )

            if not replay_result:
                return ScrapeResponse(
                    success=False, tableId=table_id, playerPerspective=player_perspective,
                    message="Failed to scrape replay", versionId=version_id,
                    indexUploaded=index_uploaded,
                )

            if replay_result.get("daily_limit_reached") or replay_result.get("error") == "replay_limit_reached":
                self.daily_limit_reached = True
                return ScrapeResponse(
                    success=False, tableId=table_id, playerPerspective=player_perspective,
                    message="Daily replay limit reached", versionId=version_id,
                    indexUploaded=index_uploaded,
                )

            replay_html = replay_result.get("html_content", "")
            if not replay_html:
                return ScrapeResponse(
                    success=False, tableId=table_id, playerPerspective=player_perspective,
                    message="No replay HTML content", versionId=version_id,
                    indexUploaded=index_uploaded,
                )

            # Build metadata fallback if table HTML parsing failed
            if not game_metadata:
                game_metadata = self.parser.convert_assignment_to_game_metadata({
                    "players": [
                        {"playerId": int(elo.player_id), "playerName": elo.player_name,
                         "position": elo.position, "arenaPoints": elo.arena_points,
                         "arenaPointsChange": elo.arena_points_change,
                         "elo": elo.game_rank, "eloChange": elo.game_rank_change}
                        for elo in elo_data.values()
                        if elo and elo.player_id
                    ],
                    "map": map_name,
                    "preludeOn": index_result.get("prelude_on"),
                    "coloniesOn": index_result.get("colonies_on"),
                    "corporateEraOn": index_result.get("corporate_era_on"),
                    "draftOn": index_result.get("draft_on"),
                    "beginnersCorporationsOn": index_result.get("beginners_corporations_on"),
                    "gameSpeed": index_result.get("game_speed"),
                    "gameMode": game_mode,
                    "playedAt": game_api_data.get("parsed_datetime"),
                })

            # Parse
            logger.info(f"[{table_id}] Parsing game data...")
            game_data = self.parser.parse_complete_game(
                replay_html=replay_html,
                game_metadata=game_metadata,
                table_id=table_id,
                player_perspective=player_perspective,
            )

            if not game_data:
                return ScrapeResponse(
                    success=False, tableId=table_id, playerPerspective=player_perspective,
                    message="Parsing failed", versionId=version_id,
                    indexUploaded=index_uploaded,
                )

            # Upload game log to API
            game_log_uploaded = False
            payload = self.parser._convert_game_data_to_api_format(game_data, table_id, player_perspective)
            if payload.get("metadata") is None:
                payload["metadata"] = {}
            payload["metadata"]["scraper_version"] = BUILD_VERSION
            if self.api.store_game_log(payload, scraped_by_email=config.BGA_EMAIL):
                game_log_uploaded = True
                logger.info(f"[{table_id}] Game log uploaded to API")
            else:
                logger.warning(f"[{table_id}] Failed to upload game log to API")

            self.games_processed += 1
            self.last_scrape_at = datetime.now().isoformat()
            duration = time.time() - start

            logger.info(f"[{table_id}] Done in {duration:.1f}s — winner={game_data.winner}, gens={game_data.generations}")

            return ScrapeResponse(
                success=True,
                tableId=table_id,
                playerPerspective=player_perspective,
                message="OK",
                versionId=version_id,
                gameMode=game_mode,
                map=game_data.map,
                generations=game_data.generations,
                winner=game_data.winner,
                conceded=game_data.conceded,
                moves=len(game_data.moves) if game_data.moves else 0,
                indexUploaded=index_uploaded,
                gameLogUploaded=game_log_uploaded,
                durationSeconds=round(duration, 1),
            )

        except Exception as e:
            logger.error(f"[{table_id}] Error: {e}", exc_info=True)
            return ScrapeResponse(
                success=False, tableId=table_id, playerPerspective=player_perspective,
                message=f"Error: {e}",
            )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

orchestrator = ScrapeOrchestrator()
scrape_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    success = await asyncio.to_thread(orchestrator.start)
    if not success:
        logger.error("Failed to start browser on startup — service will be unhealthy")
    yield
    # Shutdown
    await asyncio.to_thread(orchestrator.stop)


app = FastAPI(title="BGA TM Scraper", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _scrape_with_lock(table_id: str, player_perspective: str) -> ScrapeResponse:
    async with scrape_lock:
        return await asyncio.to_thread(orchestrator.scrape_and_upload, table_id, player_perspective)


async def _restart_with_lock() -> bool:
    async with scrape_lock:
        return await asyncio.to_thread(orchestrator.restart_browser)


@app.get("/health", response_model=HealthResponse)
async def health():
    return orchestrator.health_status()


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest):
    if not orchestrator.browser_alive:
        raise HTTPException(status_code=503, detail="Browser not started")

    if orchestrator.daily_limit_reached:
        raise HTTPException(status_code=429, detail="Daily replay limit reached")

    try:
        result = await asyncio.wait_for(
            _scrape_with_lock(req.tableId, req.playerPerspective),
            timeout=LOCK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Another scrape is in progress. Try again later.",
            headers={"Retry-After": "30"},
        )

    if result.message == "Daily replay limit reached":
        raise HTTPException(status_code=429, detail=result.message)
    if not result.success and "Failed to scrape" in result.message:
        raise HTTPException(status_code=422, detail=result.message)
    if not result.success and "Parsing failed" in result.message:
        raise HTTPException(status_code=500, detail=result.message)

    return result


@app.post("/restart-browser")
async def restart_browser():
    try:
        success = await asyncio.wait_for(_restart_with_lock(), timeout=60)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Scrape in progress, cannot restart now")

    if success:
        return {"status": "restarted"}
    else:
        raise HTTPException(status_code=500, detail="Browser restart failed")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
