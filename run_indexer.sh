#!/usr/bin/env bash
# Launch index_top_players.py via run_with_record.sh so the run shows up
# in the /jobs dashboard with a JSON record + per-run log file under ~/logs/.
#
# Runs from ~/bga-tm-scraper-indexer/ (its own config.py, separate BGA
# credentials from the web service in ~/bga-tm-scraper/). The bga_tm_scraper
# package is imported from the main repo via PYTHONPATH so the indexer
# doesn't need its own copy of the source tree or venv.
#
# Usage:
#   ./run_indexer.sh                 # default: top 100 players
#   ./run_indexer.sh -n 50           # top 50
#   ./run_indexer.sh --player-id 123 # single player
set -euo pipefail

WRAPPER="$HOME/bin/run_with_record.sh"
if [ ! -x "$WRAPPER" ]; then
    echo "Missing $WRAPPER — install it first." >&2
    exit 1
fi

cd ~/bga-tm-scraper-indexer
export PYTHONPATH=/home/azureuser/bga-tm-scraper
nohup "$WRAPPER" indexer -- \
    /home/azureuser/bga-tm-scraper/venv/bin/python -u index_top_players.py "$@" \
    >/dev/null 2>&1 < /dev/null &

PID=$!
echo "Started indexer wrapper PID=$PID"
echo "Dashboard: http://20.82.3.63:8000/jobs"
