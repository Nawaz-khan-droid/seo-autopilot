"""Pre-flight backup for the Keyword Tracker sheet.

Run before any structural change to the sheet so that if the new code
mismatches the existing layout, you can restore from the backup tab.

Usage: python scripts/backup_sheet.py

Behavior:
- Reads every protected tab (Keywords, SERP, SERP Snapshot, SERP History,
  Competitor Snapshot, AI Analysis, Website Tracking & Insights).
- Writes the full content into a new tab named
  BACKUP_<TAB>_<ISO_TIMESTAMP>.
- If a backup for the same tab already exists within the last 24h,
  it is reused (idempotent within that window).

This script does NOT modify any production tab.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow running as a plain script: add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import CREDENTIALS_PATH, SHEET_NAME
from modules.logger_config import setup_logging
from modules.sheet_client import SheetClient

logger = logging.getLogger(__name__)

PROTECTED_TABS = [
    "Keywords",
    "SERP",
    "SERP Snapshot",
    "SERP History",
    "Competitor Snapshot",
    "AI Analysis",
    "Website Tracking & Insights",
]


def _tab_exists(sheet: SheetClient, tab_name: str) -> bool:
    try:
        sheet.get_tab(tab_name)
        return True
    except Exception:
        return False


def _recent_backup_exists(sheet: SheetClient, base_name: str) -> bool:
    """If a backup tab for `base_name` exists in the last 24h, skip."""
    try:
        # List all worksheets in the spreadsheet
        for ws in sheet.spreadsheet.worksheets():
            t = ws.title
            if not t.startswith(f"BACKUP_{base_name}_"):
                continue
            # Parse timestamp suffix
            try:
                ts = t.rsplit("_", 1)[-1]
                backup_time = datetime.strptime(ts, "%Y%m%dT%H%M%S")
            except (ValueError, IndexError):
                continue
            if datetime.now() - backup_time < timedelta(hours=24):
                logger.info(
                    f"Recent backup of '{base_name}' exists: {t} "
                    f"({(datetime.now() - backup_time).seconds // 60} min ago). Skipping."
                )
                return True
    except Exception as e:
        logger.warning(f"Could not list worksheets: {e}")
    return False


def backup_tab(sheet: SheetClient, tab_name: str) -> str | None:
    if not _tab_exists(sheet, tab_name):
        logger.info(f"Tab '{tab_name}' not present in sheet. Skipping.")
        return None
    if _recent_backup_exists(sheet, tab_name):
        return None

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_name = f"BACKUP_{tab_name}_{ts}"
    try:
        ws = sheet.get_tab(tab_name)
        values = ws.get_all_values()
        if not values:
            logger.info(f"Tab '{tab_name}' is empty. Skipping backup.")
            return None
        # Build new tab
        new_ws = sheet.get_or_create_tab(backup_name, rows=max(len(values), 10), cols=max(len(values[0]) if values else 5, 5))
        new_ws.update(range_name="A1", values=values)
        logger.info(
            f"Backed up '{tab_name}' -> '{backup_name}' "
            f"({len(values)} rows)"
        )
        return backup_name
    except Exception as e:
        logger.error(f"Failed to back up '{tab_name}': {e}", exc_info=True)
        return None


def main() -> int:
    setup_logging()
    sheet = SheetClient(
        credentials_path=CREDENTIALS_PATH, sheet_name=SHEET_NAME
    )
    created: list[str] = []
    for tab in PROTECTED_TABS:
        result = backup_tab(sheet, tab)
        if result:
            created.append(result)
    if created:
        print("Created backup tabs:")
        for c in created:
            print(f"  - {c}")
    else:
        print("No new backup tabs were created (either tabs missing or recent backup exists).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
