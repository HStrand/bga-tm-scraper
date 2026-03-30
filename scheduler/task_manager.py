"""Windows Task Scheduler management for daily scraping."""

import csv
import io
import logging
import os
import subprocess
import sys
import tempfile
from typing import Optional, Dict

logger = logging.getLogger(__name__)

TASK_NAME = "BGA TM Scraper - Daily"


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
    Create or update a daily scheduled task.

    Args:
        exe_path: Full path to the executable
        working_dir: Working directory for the task
        time_str: Time in HH:MM format (24-hour)

    Returns:
        True if the task was created/updated successfully.
    """
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


def delete_task() -> bool:
    """Delete the scheduled task. Returns True if deleted or didn't exist."""
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


def query_task() -> Optional[Dict[str, str]]:
    """
    Query the scheduled task status.

    Returns:
        Dict with keys: next_run, last_run, last_result, status
        None if task doesn't exist.
    """
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


def is_task_installed() -> bool:
    """Check if the scheduled task exists."""
    return query_task() is not None


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
