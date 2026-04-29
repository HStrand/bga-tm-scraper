#!/usr/bin/env bash
# Generic job wrapper: writes a JSON run record + per-run log file, and
# updates the record with end time + exit code via an EXIT trap.
#
# Usage:
#   run_with_record.sh <job-name> -- <command> [args...]
#
# Layout (under $LOGS_ROOT, default ~/logs):
#   $LOGS_ROOT/runs/<job>_<ts>.json   one record per run
#   $LOGS_ROOT/<job>/run_<ts>.log     full stdout+stderr for that run
#
# The wrapper blocks until the command exits. Cron should call it directly;
# interactive launchers should nohup it.
set -uo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <job-name> -- <command> [args...]" >&2
    exit 2
fi

JOB="$1"
shift
if [ "${1:-}" = "--" ]; then
    shift
fi

LOGS_ROOT="${LOGS_ROOT:-$HOME/logs}"
RUNS_DIR="$LOGS_ROOT/runs"
JOB_LOG_DIR="$LOGS_ROOT/$JOB"
mkdir -p "$RUNS_DIR" "$JOB_LOG_DIR"

TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_ID="${JOB}_${TS}"
LOG_FILE="$JOB_LOG_DIR/run_${TS}.log"
RECORD="$RUNS_DIR/${RUN_ID}.json"

START_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ARGS_JSON=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@")

write_record() {
    # $1 = ended_at ISO string or "" for null
    # $2 = exit code integer or "" for null
    RUN_ID="$RUN_ID" JOB="$JOB" ARGS_JSON="$ARGS_JSON" \
    PID="$$" START_ISO="$START_ISO" LOG_FILE="$LOG_FILE" \
    ENDED_AT="$1" EXIT_CODE="$2" \
    python3 - "$RECORD" <<'PY'
import json, os, sys
ended = os.environ["ENDED_AT"] or None
code = os.environ["EXIT_CODE"]
code = int(code) if code else None
with open(sys.argv[1], "w") as f:
    json.dump({
        "run_id": os.environ["RUN_ID"],
        "job": os.environ["JOB"],
        "args": json.loads(os.environ["ARGS_JSON"]),
        "pid": int(os.environ["PID"]),
        "started_at": os.environ["START_ISO"],
        "ended_at": ended,
        "exit_code": code,
        "log_path": os.environ["LOG_FILE"],
    }, f, indent=2)
PY
}

write_record "" ""

finalize() {
    local code=$?
    write_record "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$code"
}
trap finalize EXIT

# Redirect all subsequent output to the log file
exec >> "$LOG_FILE" 2>&1
echo "=== run_with_record: job=$JOB run_id=$RUN_ID started=$START_ISO ==="
echo "=== command: $* ==="
"$@"
