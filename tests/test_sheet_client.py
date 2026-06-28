from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from gspread.exceptions import WorksheetNotFound

from modules.sheet_client import SheetClient


@pytest.fixture
def mock_gspread():
    with patch("modules.sheet_client.gspread") as mock:
        gc = MagicMock()
        mock.service_account.return_value = gc
        sheet = MagicMock()
        gc.open.return_value = sheet
        yield mock, gc, sheet


class TestSheetClient:
    def test_init_opens_sheet(self, mock_gspread):
        _, gc, sheet = mock_gspread
        client = SheetClient("creds.json", "Test Sheet")
        gc.open.assert_called_once_with("Test Sheet")
        assert client.sheet == sheet

    def test_get_tab_returns_worksheet(self, mock_gspread):
        _, _, sheet = mock_gspread
        ws = MagicMock()
        sheet.worksheet.return_value = ws
        client = SheetClient("creds.json", "Test Sheet")
        result = client.get_tab("Keywords")
        assert result == ws
        sheet.worksheet.assert_called_once_with("Keywords")

    def test_read_records(self, mock_gspread):
        _, _, sheet = mock_gspread
        ws = MagicMock()
        ws.get_all_records.return_value = [
            {"Keyword": "test", "Target URL": "https://example.com"}
        ]
        sheet.worksheet.return_value = ws
        client = SheetClient("creds.json", "Test Sheet")
        records = client.read_records("Keywords")
        assert len(records) == 1
        assert records[0]["Keyword"] == "test"

    def test_write_rows_clears_and_updates(self, mock_gspread):
        _, _, sheet = mock_gspread
        ws = MagicMock()
        ws.row_values.return_value = ["old", "headers"]
        ws.row_count = 100
        sheet.worksheet.return_value = ws
        client = SheetClient("creds.json", "Test Sheet")
        client.write_rows("SERP Snapshot", [["H1", "H2"], ["v1", "v2"]])
        ws.clear.assert_called_once()
        ws.delete_rows.assert_called_once_with(1, 99)
        ws.update.assert_called_once_with(
            range_name="A1", values=[["H1", "H2"]]
        )
        ws.append_rows.assert_called_once_with(values=[["v1", "v2"]])

    def test_write_rows_empty_does_nothing(self, mock_gspread):
        _, _, sheet = mock_gspread
        ws = MagicMock()
        sheet.worksheet.return_value = ws
        client = SheetClient("creds.json", "Test Sheet")
        client.write_rows("SERP Snapshot", [])
        ws.clear.assert_not_called()
        ws.update.assert_not_called()

    def test_ensure_headers_updates_when_different(self, mock_gspread):
        _, _, sheet = mock_gspread
        ws = MagicMock()
        ws.row_values.return_value = ["Old"]
        sheet.worksheet.return_value = ws
        client = SheetClient("creds.json", "Test Sheet")
        client.ensure_headers("AI Analysis", ["Keyword", "Recommendation"])
        ws.delete_rows.assert_called_once_with(1, 1)
        ws.update.assert_called_once()

    def test_ensure_headers_skips_when_matching(self, mock_gspread):
        _, _, sheet = mock_gspread
        ws = MagicMock()
        ws.row_values.return_value = ["Keyword", "Recommendation"]
        sheet.worksheet.return_value = ws
        client = SheetClient("creds.json", "Test Sheet")
        client.ensure_headers("AI Analysis", ["Keyword", "Recommendation"])
        ws.delete_rows.assert_not_called()
        ws.update.assert_not_called()

    def test_get_or_create_tab_returns_existing(self, mock_gspread):
        _, _, sheet = mock_gspread
        ws = MagicMock()
        sheet.worksheet.return_value = ws
        client = SheetClient("creds.json", "Test Sheet")
        result = client.get_or_create_tab("SERP History")
        assert result == ws
        sheet.add_worksheet.assert_not_called()

    def test_get_or_create_tab_creates_when_missing(self, mock_gspread):
        _, _, sheet = mock_gspread
        sheet.worksheet.side_effect = WorksheetNotFound("missing")
        new_ws = MagicMock()
        sheet.add_worksheet.return_value = new_ws
        client = SheetClient("creds.json", "Test Sheet")
        result = client.get_or_create_tab("SERP History")
        assert result == new_ws
        sheet.add_worksheet.assert_called_once_with(
            title="SERP History", rows=100, cols=20
        )
