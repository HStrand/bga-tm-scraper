"""OS-aware task scheduling for daily scraping (Windows Task Scheduler / Linux crontab)."""

import csv
import io
import logging
import os
import platform
import subprocess
import sys
import tempfile
from typing import Optional, Dict

logger = logging.getLogger(__name__)

TASK_NAME = "BGA TM Scraper - Daily"
CRON_COMMENT = "bga-tm-scraper-daily"

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"


def _build_task_xml(exe_path: str, working_dir: str, time_str: str) -> str:
    """Build a minimal Task Scheduler XML definition."""
    # time_str is HH:MM, need HH:MM:SS for the XML
    start_time = f"{time_str}:00"
    # Escape XML special characters in paths
    exe_path_esc = exe_path.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    working_dir_esc = working_dir.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2024-01-01T{start_time}</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT1H</Interval>
        <Duration>PT23H</Duration>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT4H</ExecutionTimeLimit>
  </Settings>
  <Actions>
    <Exec>
      <Command>{exe_path_esc}</Command>
      <Arguments>--scheduled-run</Arguments>
      <WorkingDirectory>{working_dir_esc}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""


def create_or_update_task(exe_path: str, working_dir: str, time_str: str) -> bool:
    """
    Create or update a daily scheduled task (OS-aware).

    Args:
        exe_path: Full path to the executable
        working_dir: Working directory for the task
        time_str: Time in HH:MM format (24-hour)

    Returns:
        True if the task was created/updated successfully.
    """
    if IS_WINDOWS:
        return _win_create_or_update_task(exe_path, working_dir, time_str)
    elif IS_LINUX:
        return _linux_create_or_update_cron(exe_path, working_dir, time_str)
    else:
        logger.error(f"Scheduling not supported on {platform.system()}")
        return False


def delete_task() -> bool:
    """Delete the scheduled task. Returns True if deleted or didn't exist."""
    if IS_WINDOWS:
        return _win_delete_task()
    elif IS_LINUX:
        return _linux_delete_cron()
    else:
        logger.error(f"Scheduling not supported on {platform.system()}")
        return False


def query_task() -> Optional[Dict[str, str]]:
    """
    Query the scheduled task status.

    Returns:
        Dict with keys: next_run, last_run, last_result, status
        None if task doesn't exist.
    """
    if IS_WINDOWS:
        return _win_query_task()
    elif IS_LINUX:
        return _linux_query_cron()
    else:
        return None


def is_task_installed() -> bool:
    """Check if the scheduled task exists."""
    return query_task() is not None


# ---------------------------------------------------------------------------
# Windows Task Scheduler
# ---------------------------------------------------------------------------

def _win_create_or_update_task(exe_path: str, working_dir: str, time_str: str) -> bool:
    xml_content = _build_task_xml(exe_path, working_dir, time_str)

    try:
        # Write XML to a temp file — schtasks requires UTF-16 LE with BOM
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".xml", delete=False) as tmp:
            tmp.write(b'\xff\xfe')  # UTF-16 LE BOM
            tmp.write(xml_content.encode("utf-16-le"))
            tmp_path = tmp.name

        result = subprocess.run(
            ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", tmp_path, "/F"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        os.unlink(tmp_path)

        if result.returncode == 0:
            logger.info(f"Scheduled task '{TASK_NAME}' created/updated for {time_str}")
            return True
        else:
            logger.error(f"schtasks /Create failed: {result.stderr.strip()}")
            return False

    except FileNotFoundError:
        logger.error("schtasks.exe not found")
        return False
    except subprocess.TimeoutExpired:
        logger.error("schtasks /Create timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to create scheduled task: {e}")
        return False


def _win_delete_task() -> bool:
    """Delete the Windows scheduled task. Returns True if deleted or didn't exist."""
    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            logger.info(f"Scheduled task '{TASK_NAME}' deleted")
            return True
        # Task didn't exist — that's fine
        if "cannot find" in result.stderr.lower() or "does not exist" in result.stderr.lower():
            return True
        logger.error(f"schtasks /Delete failed: {result.stderr.strip()}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete scheduled task: {e}")
        return False


def _win_query_task() -> Optional[Dict[str, str]]:
    """Query the Windows scheduled task status."""
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "CSV", "/V"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None

        reader = csv.DictReader(io.StringIO(result.stdout))
        for row in reader:
            return {
                "next_run": row.get("Next Run Time", "").strip(),
                "last_run": row.get("Last Run Time", "").strip(),
                "last_result": row.get("Last Result", "").strip(),
                "status": row.get("Status", "").strip(),
                "task_name": row.get("TaskName", "").strip(),
            }
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Linux crontab
# ---------------------------------------------------------------------------

def _get_current_crontab() -> str:
    """Read the current user's crontab. Returns empty string if none."""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout
        return ""
    except Exception:
        return ""


def _write_crontab(content: str) -> bool:
    """Write a new crontab for the current user."""
    try:
        proc = subprocess.run(
            ["crontab", "-"],
            input=content, capture_output=True, text=True, timeout=10,
        )
        return proc.returncode == 0
    except Exception as e:
        logger.error(f"Failed to write crontab: {e}")
        return False


def _build_cron_line(exe_path: str, working_dir: str, time_str: str) -> str:
    """Build a crontab line for the daily scraping job."""
    parts = time_str.split(":")
    hour = parts[0] if len(parts) >= 1 else "3"
    minute = parts[1] if len(parts) >= 2 else "0"

    # Use python3 for .py files, direct path for frozen executables
    if exe_path.endswith(".py"):
        python = sys.executable or "python3"
        command = f"cd {working_dir} && {python} {exe_path} --scheduled-run"
    else:
        command = f"cd {working_dir} && {exe_path} --scheduled-run"

    return f"{minute} {hour} * * * {command} # {CRON_COMMENT}"


def _linux_create_or_update_cron(exe_path: str, working_dir: str, time_str: str) -> bool:
    """Create or update the crontab entry for daily scraping."""
    try:
        existing = _get_current_crontab()

        # Remove any existing entry for this app
        lines = [
            line for line in existing.splitlines()
            if CRON_COMMENT not in line
        ]

        # Add our new entry
        new_line = _build_cron_line(exe_path, working_dir, time_str)
        lines.append(new_line)

        # Ensure trailing newline (crontab requires it)
        new_crontab = "\n".join(lines).strip() + "\n"

        if _write_crontab(new_crontab):
            logger.info(f"Cron job created/updated for {time_str}")
            return True
        else:
            logger.error("Failed to write crontab")
            return False
    except Exception as e:
        logger.error(f"Failed to create cron job: {e}")
        return False


def _linux_delete_cron() -> bool:
    """Remove the crontab entry. Returns True if removed or didn't exist."""
    try:
        existing = _get_current_crontab()
        lines = [
            line for line in existing.splitlines()
            if CRON_COMMENT not in line
        ]

        new_crontab = "\n".join(lines).strip()
        if new_crontab:
            new_crontab += "\n"
            return _write_crontab(new_crontab)
        else:
            # No entries left, remove crontab entirely
            subprocess.run(["crontab", "-r"], capture_output=True, timeout=10)
            return True
    except Exception as e:
        logger.error(f"Failed to delete cron job: {e}")
        return False


def _linux_query_cron() -> Optional[Dict[str, str]]:
    """Query whether the cron job is installed and return status info."""
    try:
        existing = _get_current_crontab()
        for line in existing.splitlines():
            if CRON_COMMENT in line:
                # Parse the time from the cron expression
                parts = line.strip().split()
                if len(parts) >= 5:
                    minute = parts[0]
                    hour = parts[1]
                    next_run = f"Daily at {hour.zfill(2)}:{minute.zfill(2)}"
                else:
                    next_run = "Daily (see crontab)"
                return {
                    "next_run": next_run,
                    "last_run": "See scheduler.log",
                    "last_result": "",
                    "status": "Installed",
                    "task_name": CRON_COMMENT,
                }
        return None
    except Exception:
        return None


def get_exe_path() -> str:
    """Get the path to the current executable (works for both dev and PyInstaller)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "gui_main.py"))


def get_working_dir() -> str:
    """Get the working directory (where config.json lives)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
