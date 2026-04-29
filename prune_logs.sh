#!/usr/bin/env bash
# Weekly cleanup: delete files older than 30 days under ~/logs/, append a
# one-line per-dir summary (count + freed bytes) to ~/logs/cleanup.log.
set -uo pipefail

LOGS_ROOT="${LOGS_ROOT:-$HOME/logs}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
SUMMARY_LOG="$LOGS_ROOT/cleanup.log"

mkdir -p "$LOGS_ROOT"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

prune_dir() {
    local dir="$1"
    [ -d "$dir" ] || return 0
    local bytes count
    bytes=$(find "$dir" -type f -mtime "+$RETENTION_DAYS" -printf '%s\n' 2>/dev/null \
            | awk 'BEGIN{s=0} {s+=$1} END{print s+0}')
    count=$(find "$dir" -type f -mtime "+$RETENTION_DAYS" -delete -print 2>/dev/null | wc -l)
    echo "$TS dir=$dir deleted=$count freed_bytes=$bytes" >> "$SUMMARY_LOG"
}

# Per-job log dirs (anything under ~/logs/ except runs/ and the summary log itself)
for d in "$LOGS_ROOT"/*/; do
    [ "$(basename "$d")" = "runs" ] && continue
    prune_dir "$d"
done

# Run records
prune_dir "$LOGS_ROOT/runs"
