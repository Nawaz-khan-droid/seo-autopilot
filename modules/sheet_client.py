from __future__ import annotations

import logging
import time
from typing import Any

import gspread
from gspread import Worksheet
from gspread.exceptions import APIError, WorksheetNotFound
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)

_API_DELAY = 0.6  # seconds between sheet API writes to avoid 429
_SHEET_RETRIES = 3


def _rate_limited_call(fn, *args, **kwargs):
    time.sleep(_API_DELAY)
    for attempt in range(_SHEET_RETRIES):
        try:
            return fn(*args, **kwargs)
        except APIError as e:
            if "429" in str(e):
                wait = 2 ** (attempt + 1)
                logger.warning(
                    f"Sheet 429 on {fn.__name__} "
                    f"(attempt {attempt + 1}/{_SHEET_RETRIES}), "
                    f"retrying after {wait}s..."
                )
                time.sleep(wait)
                continue
            raise
    # Final attempt after all retries exhausted
    return fn(*args, **kwargs)


class SheetClient:
    def __init__(self, credentials_path: str, sheet_name: str | None = None, sheet_url: str | None = None) -> None:
        self.gc = gspread.service_account(filename=credentials_path)
        if sheet_url:
            self.sheet = self.gc.open_by_url(sheet_url)
            logger.info("Connected to sheet by URL")
        else:
            self.sheet = self.gc.open(sheet_name or "")
            logger.info(f"Connected to sheet: {sheet_name}")

    def get_tab(self, tab_name: str) -> Worksheet:
        return self.sheet.worksheet(tab_name)

    def get_or_create_tab(self, tab_name: str, rows: int = 100, cols: int = 20) -> Worksheet:
        try:
            return self.sheet.worksheet(tab_name)
        except WorksheetNotFound:
            ws = self.sheet.add_worksheet(title=tab_name, rows=rows, cols=cols)
            logger.info(f"Created new tab '{tab_name}'")
            return ws

    def read_records(self, tab_name: str) -> list[dict[str, Any]]:
        return self.get_tab(tab_name).get_all_records()

    def read_range(self, tab_name: str, range_name: str) -> list[list[str]]:
        return self.get_tab(tab_name).range(range_name)

    def ensure_headers(
        self, tab_name: str, expected_headers: list[str]
    ) -> None:
        ws = self.get_tab(tab_name)
        existing = ws.row_values(1)
        if existing != expected_headers:
            existing_count = len(existing) if existing != [""] else 0
            if existing_count > 0:
                _rate_limited_call(ws.delete_rows, 1, existing_count)
            _rate_limited_call(ws.update, range_name="A1", values=[expected_headers])
            logger.info(f"Updated headers for tab '{tab_name}'")

    def clear_tab(self, tab_name: str) -> None:
        ws = self.get_tab(tab_name)
        _rate_limited_call(ws.clear)
        logger.info(f"Cleared tab '{tab_name}'")

    def write_rows(
        self, tab_name: str, rows: list[list[Any]]
    ) -> None:
        if not rows:
            return
        ws = self.get_tab(tab_name)
        existing = ws.row_values(1)
        if existing and existing != [""]:
            _rate_limited_call(ws.clear)
            if ws.row_count > 2:
                _rate_limited_call(ws.delete_rows, 1, ws.row_count - 1)
        _rate_limited_call(ws.update, range_name="A1", values=[rows[0]])
        if len(rows) > 1:
            _rate_limited_call(ws.append_rows, values=rows[1:])
        logger.info(f"Wrote {len(rows)} rows to tab '{tab_name}'")

    def append_rows(
        self, tab_name: str, rows: list[list[Any]]
    ) -> None:
        if not rows:
            return
        ws = self.get_tab(tab_name)
        _rate_limited_call(ws.append_rows, values=rows, value_input_option="USER_ENTERED")
        logger.info(f"Appended {len(rows)} rows to tab '{tab_name}'")
