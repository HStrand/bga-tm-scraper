"""JSON-backed history store for scheduled scraping runs."""

import json
import os
from typing import Dict, List, Any

HISTORY_FILE = "scheduler_history.json"
MAX_ENTRIES = 90


def _get_history_path() -> str:
    """Return the path to the history file, next to the executable/script."""
    if getattr(os.sys, "frozen", False):
        base = os.path.dirname(os.sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, HISTORY_FILE)


def load_history() -> List[Dict[str, Any]]:
    """Load run history from disk. Returns empty list if file doesn't exist."""
    path = _get_history_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def append_run(entry: Dict[str, Any]) -> None:
    """
    Append a run entry and save. Trims to MAX_ENTRIES most recent.

    Expected entry keys:
        date, processed, successes, failures, limit_reached, duration_seconds
    """
    history = load_history()
    history.append(entry)
    if len(history) > MAX_ENTRIES:
        history = history[-MAX_ENTRIES:]
    path = _get_history_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
