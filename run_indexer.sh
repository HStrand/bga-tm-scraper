#!/usr/bin/env bash
# Launch index_top_players.py in the background with a timestamped log file.
# A symlink at /tmp/index_top_players_current.log always points at the active run.
#
# Intended for use on the Azure VM where the indexer runs from
# ~/bga-tm-scraper-indexer/ with its own config.py (separate BGA credentials
# from the web service in ~/bga-tm-scraper/). The bga_tm_scraper package is
# imported from the main repo via PYTHONPATH so the indexer doesn't need its
# own copy of the source tree or venv.
#
# Usage:
#   ./run_indexer.sh                 # default: top 100 players
#   ./run_indexer.sh -n 50           # top 50
#   ./run_indexer.sh --player-id 123 # single player
set -euo pipefail

LOG_DIR=/tmp
TS=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/index_top_players_$TS.log"
CURRENT_LINK="$LOG_DIR/index_top_players_current.log"

cd ~/bga-tm-scraper-indexer
PYTHONPATH=/home/azureuser/bga-tm-scraper nohup \
    /home/azureuser/bga-tm-scraper/venv/bin/python -u index_top_players.py "$@" \
    >> "$LOG_FILE" 2>&1 < /dev/null &
PID=$!

ln -sfn "$LOG_FILE" "$CURRENT_LINK"

echo "Started indexer PID=$PID"
echo "Log file: $LOG_FILE"
echo "Current symlink: $CURRENT_LINK -> $LOG_FILE"
