from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from config.location_map import normalize_location
from modules.url_utils import exact_url_match
from orchestrator.ai_analysis import (
    AI_HEADERS,
    SYSTEM_PROMPT_PATH,
    AiAnalysisWorkflow,
    _load_system_prompt,
)
from orchestrator.serp_snapshot import (
    COMPETITOR_HEADERS,
    DuplicateDateColumnError,
    HISTORY_HEADERS,
    SERP_DISPLAY_STATIC_HEADERS,
    SERP_HEADERS,
    SerpSnapshotWorkflow,
    SerpTabSchemaError,
)
from orchestrator.website_insights import (
    INSIGHTS_HEADERS,
    GSC_ACCESS_REQUIRED,
    WebsiteInsightsWorkflow,
)
from tests.conftest import (
    SAMPLE_APIFY_BATCH,
    SAMPLE_GROQ_RESPONSE,
    SAMPLE_KEYWORDS_RECORDS,
    SAMPLE_SEARCHAPI_RESPONSE,
    SAMPLE_SERP_RESPONSE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_sheet(keywords_records):
    """Build a MagicMock sheet that:
    - returns the keywords records from the 'Keywords' tab
    - returns empty records for all other tabs
    - tracks get_or_create_tab calls
    """
    sheet = MagicMock()

    def tab_side_effect(name):
        ws = MagicMock()
        if name == "Keywords":
            ws.get_all_records.return_value = keywords_records
        else:
            ws.get_all_records.return_value = []
            ws.get_all_values.return_value = []
        ws.row_values.return_value = []
        return ws

    sheet.get_tab.side_effect = tab_side_effect
    return sheet


def _apify_mock_with_batch(batch=None):
    apify = MagicMock()
    apify.search_batch.return_value = batch or SAMPLE_APIFY_BATCH
    apify.search.return_value = (
        SAMPLE_APIFY_BATCH.get("seo services mumbai")
        or {"organic_results": [], "ai_overview": None, "people_also_ask": []}
    )
    return apify


# ---------------------------------------------------------------------------
# Header / schema tests
# ---------------------------------------------------------------------------
class TestSerpSnapshotHeaders:
    def test_serp_headers_count(self):
        assert len(SERP_HEADERS) == 10

    def test_serp_headers_omit_local_maps_and_paid_ads(self):
        for forbidden in ("Local Maps", "Paid Ads", "Raw SERP Status"):
            assert forbidden not in SERP_HEADERS

    def test_serp_headers_contain_feature_columns(self):
        assert "AI Overview Mention" in SERP_HEADERS
        assert "PAA Mention" in SERP_HEADERS

    def test_serp_display_static_headers(self):
        assert SERP_DISPLAY_STATIC_HEADERS == [
            "Keyword", "Target URL", "Search Location", "Device", "Search Intent",
        ]

    def test_history_headers_count(self):
        assert HISTORY_HEADERS == ["Timestamp", "Keyword", "Position", "Ranking URL"]

    def test_competitor_headers_count(self):
        assert len(COMPETITOR_HEADERS) == 9
        assert COMPETITOR_HEADERS[0] == "Keyword"
        assert COMPETITOR_HEADERS[-1] == "Last Updated"


# ---------------------------------------------------------------------------
# SERP display tab validation
# ---------------------------------------------------------------------------
class TestSerpTabSchemaValidation:
    def _workflow(self, sheet):
        serp = MagicMock()
        serp.search.return_value = SAMPLE_SERP_RESPONSE
        return SerpSnapshotWorkflow(sheet=sheet, serp=serp, max_keywords=3)

    def test_missing_keyword_column_raises(self):
        sheet = MagicMock()
        ws = MagicMock()
        ws.get_all_values.return_value = [
            ["Target URL", "Location", "Device", "Search Intent", "Rank"],
            ["", "", "", "", "2026-06-06"],
        ]
        sheet.get_or_create_tab.return_value = ws
        with __import__("pytest").raises(SerpTabSchemaError):
            self._workflow(sheet)._validate_serp_tab_static_headers(
                ws.get_all_values.return_value[0]
            )

    def test_swapped_columns_raises(self):
        sheet = MagicMock()
        ws = MagicMock()
        ws.get_all_values.return_value = [
            ["Keyword", "Location", "Target URL", "Device", "Search Intent"],
            ["", "", "", "", "2026-06-06"],
        ]
        sheet.get_or_create_tab.return_value = ws
        with __import__("pytest").raises(SerpTabSchemaError):
            self._workflow(sheet)._validate_serp_tab_static_headers(
                ws.get_all_values.return_value[0]
            )

    def test_duplicate_iso_dates_raises(self):
        sheet = MagicMock()
        ws = MagicMock()
        ws.get_all_values.return_value = [
            list(SERP_DISPLAY_STATIC_HEADERS) + ["Rank", "Rank"],
            ["", "", "", "", "", "2026-06-06", "2026-06-06"],
        ]
        sheet.get_or_create_tab.return_value = ws
        workflow = self._workflow(sheet)
        with __import__("pytest").raises(DuplicateDateColumnError):
            workflow._find_or_append_date_column(
                ws, ws.get_all_values.return_value[0],
                ws.get_all_values.return_value[1], "2026-06-07",
            )

    def test_whitespace_in_date_header_is_recognized(self):
        sheet = MagicMock()
        ws = MagicMock()
        ws.get_all_values.return_value = [
            list(SERP_DISPLAY_STATIC_HEADERS) + ["Rank"],
            ["", "", "", "", "", " 2026-06-06 "],  # whitespace
        ]
        sheet.get_or_create_tab.return_value = ws
        workflow = self._workflow(sheet)
        idx = workflow._find_or_append_date_column(
            ws, ws.get_all_values.return_value[0],
            ws.get_all_values.return_value[1], "2026-06-06",
        )
        assert idx == 5  # existing column reused after normalization

    def test_non_iso_date_logs_warning(self, caplog):
        import logging
        sheet = MagicMock()
        ws = MagicMock()
        ws.get_all_values.return_value = [
            list(SERP_DISPLAY_STATIC_HEADERS) + ["June"],  # non-ISO label
            ["", "", "", "", "", "June"],
        ]
        sheet.get_or_create_tab.return_value = ws
        workflow = self._workflow(sheet)
        with caplog.at_level(logging.WARNING, logger="orchestrator.serp_snapshot"):
            idx = workflow._find_or_append_date_column(
                ws, ws.get_all_values.return_value[0],
                ws.get_all_values.return_value[1], "2026-06-06",
            )
        # "June" is not ISO; new date column gets appended
        assert idx == 6
        assert any("non-ISO" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# SERP run() — basic flow
# ---------------------------------------------------------------------------
class TestSerpSnapshotRun:
    def test_skips_incomplete_rows(self):
        sheet = _build_sheet(SAMPLE_KEYWORDS_RECORDS)
        serp = MagicMock()
        serp.search.return_value = SAMPLE_SERP_RESPONSE
        workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=10,
            apify=_apify_mock_with_batch(),
        )
        output = workflow.run()
        # header + 2 valid rows (3rd has empty URL)
        assert len(output) == 3

    def test_run_adds_iso_timestamp_and_position(self):
        sheet = _build_sheet([
            {
                "Keyword": "seo services mumbai",
                "Target URL": "https://www.target-site.com/products",
                "Location": "Mumbai",
                "Device": "Desktop",
                "Search Intent": "Local Commercial",
                "Active": "TRUE",
            }
        ])
        serp = MagicMock()
        serp.search.return_value = SAMPLE_SERP_RESPONSE
        workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=3,
            apify=_apify_mock_with_batch(),
        )
        output = workflow.run()
        row = output[1]
        assert row[2] == "Mumbai, Maharashtra, India"  # Search Location
        assert row[3] == "Desktop"
        assert row[4] != ""  # Run Date timestamp
        assert row[5] == "3"  # Position

    def test_inactive_keyword_is_skipped(self):
        sheet = _build_sheet([
            {
                "Keyword": "seo services mumbai",
                "Target URL": "https://www.target-site.com/products",
                "Location": "Mumbai",
                "Device": "Desktop",
                "Active": "FALSE",
            }
        ])
        serp = MagicMock()
        workflow = SerpSnapshotWorkflow(sheet=sheet, serp=serp, max_keywords=3)
        output = workflow.run()
        assert len(output) == 1  # only header

    def test_keywords_param_overrides_sheet_read(self):
        sheet = MagicMock()
        serp = MagicMock()
        serp.search.return_value = SAMPLE_SERP_RESPONSE
        keywords = [
            {
                "Keyword": "kw from param",
                "Target URL": "https://www.target-site.com/products",
                "Location": "Mumbai",
                "Device": "Desktop",
                "Active": "TRUE",
            }
        ]
        workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=3,
            apify=_apify_mock_with_batch(),
        )
        workflow.run(keywords=keywords)
        # The Keywords tab is not read when keywords are passed in.
        # (SERP Snapshot and SERP tab may still be touched for output.)
        called_tabs = [c.args[0] for c in sheet.get_tab.call_args_list]
        assert "Keywords" not in called_tabs

    def test_error_sets_position_to_not_found(self):
        sheet = _build_sheet([SAMPLE_KEYWORDS_RECORDS[0]])
        serp = MagicMock()
        serp.search.side_effect = RuntimeError("API timeout")
        workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=3,
            apify=None,  # disable apify rank participation
        )
        output = workflow.run()
        # No searchapi fallback → position remains "Not Found"
        assert output[1][5] == "Not Found"


# ---------------------------------------------------------------------------
# Provider rank hierarchy + breaker
# ---------------------------------------------------------------------------
class TestProviderHierarchy:
    def test_searchapi_only_called_when_others_miss(self):
        sheet = _build_sheet([
            {
                "Keyword": "kw",
                "Target URL": "https://www.target-site.com/products",
                "Location": "Mumbai",
                "Device": "Desktop",
                "Active": "TRUE",
            }
        ])
        serp = MagicMock()
        serp.search.return_value = SAMPLE_SERP_RESPONSE  # finds it at pos 3
        searchapi = MagicMock()
        workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=3,
            searchapi=searchapi, apify=None,
        )
        workflow.run()
        searchapi.search.assert_not_called()  # SerpApi found it

    def test_searchapi_called_when_serpapi_misses(self):
        sheet = _build_sheet([
            {
                "Keyword": "kw",
                "Target URL": "https://www.target-site.com/services",
                "Location": "Mumbai",
                "Device": "Desktop",
                "Active": "TRUE",
            }
        ])
        serp = MagicMock()
        serp.search.return_value = {
            "organic_results": [
                {"position": 1, "link": "https://other.com/page", "title": "x"},
            ]
        }
        searchapi = MagicMock()
        searchapi.search.return_value = SAMPLE_SEARCHAPI_RESPONSE
        workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=3,
            searchapi=searchapi, apify=None,
        )
        workflow.run()
        serp.search.assert_called_once()
        searchapi.search.assert_called_once()

    def test_provider_breaker_opens_after_3_hard_errors(self):
        # Use a single keyword, force 3 hard errors from SerpApi.
        sheet = _build_sheet([SAMPLE_KEYWORDS_RECORDS[0]])
        serp = MagicMock()
        serp.search.side_effect = RuntimeError("401 Unauthorized")
        apify = _apify_mock_with_batch({})  # apify batch returns nothing
        workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=1,
            apify=apify, searchapi=None,
            provider_order=["serpapi", "apify"],
        )
        # First call: serpapi raises hard error, counted.
        # Same for 2 more reruns would not happen; we simulate by
        # manually invoking the breaker.
        workflow._record_hard_error("serpapi")
        workflow._record_hard_error("serpapi")
        workflow._record_hard_error("serpapi")
        assert not workflow._provider_available("serpapi")
        assert workflow._provider_available("apify")

    def test_breaker_resets_at_start_of_run(self):
        sheet = _build_sheet([SAMPLE_KEYWORDS_RECORDS[0]])
        serp = MagicMock()
        serp.search.return_value = SAMPLE_SERP_RESPONSE
        workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=1,
            apify=None, searchapi=None,
        )
        workflow._breaker = {"serpapi": 5}
        workflow._provider_open = {"serpapi"}
        workflow.run()
        # After run, breaker is reset (the run() resets at start)
        assert workflow._breaker["serpapi"] == 0
        assert "serpapi" not in workflow._provider_open

    def test_classify_hard_error(self):
        assert SerpSnapshotWorkflow._classify_error(
            RuntimeError("401 Unauthorized")
        ) == "hard"
        assert SerpSnapshotWorkflow._classify_error(
            RuntimeError("429 quota exceeded")
        ) == "hard"
        assert SerpSnapshotWorkflow._classify_error(
            RuntimeError("InvalidApiKey")
        ) == "hard"
        # Recoverable
        assert SerpSnapshotWorkflow._classify_error(
            RuntimeError("ConnectionError: timeout")
        ) == "recoverable"
        assert SerpSnapshotWorkflow._classify_error(
            RuntimeError("some other error")
        ) == "recoverable"


# ---------------------------------------------------------------------------
# AI Overview / PAA classification
# ---------------------------------------------------------------------------
class TestFeatureClassification:
    def _workflow(self):
        sheet = MagicMock()
        serp = MagicMock()
        return SerpSnapshotWorkflow(sheet=sheet, serp=serp, max_keywords=1)

    def test_ai_overview_yes_when_target_in_sources(self):
        w = self._workflow()
        item = {
            "ai_overview": {
                "sources": [{"url": "https://www.target-site.com/page"}]
            }
        }
        assert w._classify_ai_overview(
            item, "https://www.target-site.com/page"
        ) == "YES"

    def test_ai_overview_no_when_target_absent(self):
        w = self._workflow()
        item = {
            "ai_overview": {
                "sources": [{"url": "https://other.com/page"}]
            }
        }
        assert w._classify_ai_overview(
            item, "https://www.target-site.com/page"
        ) == "NO"

    def test_ai_overview_na_when_block_absent(self):
        w = self._workflow()
        item = {"ai_overview": None}
        assert w._classify_ai_overview(
            item, "https://www.target-site.com/page"
        ) == "N/A"
        # And when the key is missing entirely
        assert w._classify_ai_overview(
            {}, "https://www.target-site.com/page"
        ) == "N/A"

    def test_paa_yes_when_target_in_item(self):
        w = self._workflow()
        item = {
            "people_also_ask": [
                {"question": "x", "url": "https://www.target-site.com/page"},
            ]
        }
        assert w._classify_paa(
            item, "https://www.target-site.com/page"
        ) == "YES"

    def test_paa_no_when_target_absent(self):
        w = self._workflow()
        item = {
            "people_also_ask": [
                {"question": "x", "url": "https://other.com/page"},
            ]
        }
        assert w._classify_paa(
            item, "https://www.target-site.com/page"
        ) == "NO"

    def test_paa_na_when_list_missing(self):
        w = self._workflow()
        assert self._workflow()._classify_paa(
            {"people_also_ask": []}, "https://www.target-site.com/page"
        ) == "N/A"
        assert self._workflow()._classify_paa(
            {}, "https://www.target-site.com/page"
        ) == "N/A"


# ---------------------------------------------------------------------------
# AI Analysis workflow
# ---------------------------------------------------------------------------
class TestAiAnalysisWorkflow:
    def test_ai_headers_match_spec(self):
        assert AI_HEADERS == [
            "Date", "Keyword", "Observed Change",
            "Likely Cause", "Recommendation", "Priority",
        ]

    def test_parse_analysis_handles_valid_response(self):
        parsed = AiAnalysisWorkflow._parse_analysis(SAMPLE_GROQ_RESPONSE)
        assert parsed["change"] == "Dropped 2 positions from rank 1 to rank 3"
        assert parsed["priority"] == "High"
        assert "Competitor published" in parsed["cause"]

    def test_parse_analysis_handles_malformed_response(self):
        parsed = AiAnalysisWorkflow._parse_analysis("garbage output\nno format\nhere")
        assert parsed["change"] == "No change detected"
        assert parsed["priority"] == "Medium"

    def test_parse_analysis_case_insensitive(self):
        text = "CHANGE: Dropped\nCAUSE: Competition\nRECOMMENDATION: Update content\nPRIORITY: HIGH"
        parsed = AiAnalysisWorkflow._parse_analysis(text)
        assert parsed["change"] == "Dropped"
        assert parsed["priority"] == "High"

    def test_fallback_analysis_with_no_history(self):
        fallback = AiAnalysisWorkflow._fallback_analysis("3")
        assert "3" in fallback["change"]
        assert "Groq API call failed" in fallback["cause"]
        assert fallback["priority"] == "Medium"

    def test_fallback_analysis_with_prev_position(self):
        fallback = AiAnalysisWorkflow._fallback_analysis("3", prev_position="1")
        assert "3" in fallback["change"]
        assert "1" in fallback["change"]
        assert "Dropped" in fallback["change"]

    def test_compute_delta_improved(self):
        assert AiAnalysisWorkflow._compute_delta("5", "2") == "Improved by 3 positions"

    def test_compute_delta_dropped(self):
        assert AiAnalysisWorkflow._compute_delta("1", "4") == "Dropped by 3 positions"

    def test_compute_delta_unchanged(self):
        assert AiAnalysisWorkflow._compute_delta("3", "3") == "No change"

    def test_compute_delta_invalid_values(self):
        assert AiAnalysisWorkflow._compute_delta("abc", "xyz") == "Unable to compute"

    def test_load_system_prompt_returns_prompt(self, tmp_path: Path) -> None:
        prompt_dir = tmp_path / "config" / "prompts"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "llm_system_prompt.txt"
        prompt_file.write_text("You are an SEO expert", encoding="utf-8")
        result = _load_system_prompt(prompt_file)
        assert result == "You are an SEO expert"

    def test_run_includes_historical_context_when_available(self):
        sheet = MagicMock()
        snapshot_ws = MagicMock()
        snapshot_ws.get_all_records.return_value = [
            {
                "Keyword": "seo services mumbai",
                "Target URL": "https://www.target-site.com/services",
                "Search Location": "Mumbai, Maharashtra, India",
                "Device": "Desktop",
                "Position": "3",
                "Ranking URL": "https://www.target-site.com/services",
                "AI Overview Mention": "YES",
                "PAA Mention": "N/A",
            }
        ]

        def tab_side_effect(name):
            if name == "SERP Snapshot":
                return snapshot_ws
            if name == "SERP History":
                hist_ws = MagicMock()
                hist_ws.get_all_records.return_value = [
                    {"Keyword": "seo services mumbai", "Position": "1"}
                ]
                return hist_ws
            ws = MagicMock()
            ws.get_all_records.return_value = []
            return ws

        sheet.get_tab.side_effect = tab_side_effect
        sheet.get_or_create_tab.return_value = MagicMock()
        groq = MagicMock()
        groq.chat.return_value = SAMPLE_GROQ_RESPONSE

        workflow = AiAnalysisWorkflow(sheet=sheet, groq=groq)
        output = workflow.run()

        assert len(output) == 2
        groq.chat.assert_called_once()
        prompt = groq.chat.call_args[1]["prompt"]
        assert "Previous position: 1" in prompt
        assert "Dropped by 2 positions" in prompt
        assert "AI Overview Mention: YES" in prompt
        assert "PAA Mention: N/A" in prompt

    def test_run_passes_keywords_to_workflow(self):
        sheet = MagicMock()
        sheet.get_tab.return_value = MagicMock(get_all_records=MagicMock(return_value=[]))
        groq = MagicMock()
        keywords = [{"Keyword": "kw", "Target URL": "https://x.com/"}]
        workflow = AiAnalysisWorkflow(sheet=sheet, groq=groq, keywords=keywords)
        # Should not raise; the workflow reads SERP Snapshot not Keywords
        # for analysis, so passing keywords is allowed (used in main.py
        # for consistency, not by run()).
        assert workflow.keywords == keywords


# ---------------------------------------------------------------------------
# Website Insights
# ---------------------------------------------------------------------------
class TestWebsiteInsightsWorkflow:
    def test_insights_headers_match_spec(self):
        assert INSIGHTS_HEADERS == [
            "URL", "Mobile PSI", "Desktop PSI", "Clicks", "Impressions",
        ]

    def test_insights_headers_count_is_5(self):
        assert len(INSIGHTS_HEADERS) == 5

    def test_run_collects_unique_urls(self):
        sheet = _build_sheet(SAMPLE_KEYWORDS_RECORDS)
        pagespeed = MagicMock()
        pagespeed.analyze_both.return_value = {"mobile": 72.3, "desktop": 88.5}

        workflow = WebsiteInsightsWorkflow(
            sheet=sheet, pagespeed=pagespeed, gsc=None
        )
        output = workflow.run()

        # 2 unique URLs + header
        assert len(output) == 3
        assert output[1][0] == "https://www.target-site.com/services"
        assert output[2][0] == "https://www.target-site.com/about"

    def test_gsc_group_cells_always_match_when_missing(self):
        """When GSC is not configured, BOTH Clicks and Impressions must be
        'Access Required' — never a mix."""
        sheet = _build_sheet([SAMPLE_KEYWORDS_RECORDS[0]])
        pagespeed = MagicMock()
        pagespeed.analyze_both.return_value = {"mobile": 72.3, "desktop": 88.5}

        workflow = WebsiteInsightsWorkflow(
            sheet=sheet, pagespeed=pagespeed, gsc=None
        )
        output = workflow.run()
        row = output[1]
        assert row[3] == GSC_ACCESS_REQUIRED  # Clicks
        assert row[4] == GSC_ACCESS_REQUIRED  # Impressions

    def test_gsc_group_cells_always_match_when_status_error(self):
        """When GSC returns status != 'ok', BOTH cells become
        'Access Required' — never one real and the other 'Access
        Required'."""
        sheet = _build_sheet([SAMPLE_KEYWORDS_RECORDS[0]])
        pagespeed = MagicMock()
        pagespeed.analyze_both.return_value = {"mobile": 80.0, "desktop": 90.0}
        gsc = MagicMock()
        gsc.query.return_value = {"status": "error", "total_clicks": 999,
                                   "total_impressions": 999}

        workflow = WebsiteInsightsWorkflow(
            sheet=sheet, pagespeed=pagespeed, gsc=gsc
        )
        output = workflow.run()
        row = output[1]
        # Even though gsc returned numbers, status is "error", so
        # both cells should fall back to "Access Required".
        assert row[3] == GSC_ACCESS_REQUIRED
        assert row[4] == GSC_ACCESS_REQUIRED

    def test_gsc_group_cells_match_when_ok(self):
        sheet = _build_sheet([SAMPLE_KEYWORDS_RECORDS[0]])
        pagespeed = MagicMock()
        pagespeed.analyze_both.return_value = {"mobile": 80.0, "desktop": 90.0}
        gsc = MagicMock()
        gsc.query.return_value = {
            "status": "ok",
            "total_clicks": 142,
            "total_impressions": 8430,
        }

        workflow = WebsiteInsightsWorkflow(
            sheet=sheet, pagespeed=pagespeed, gsc=gsc
        )
        output = workflow.run()
        row = output[1]
        assert row[3] == 142
        assert row[4] == 8430

    def test_pagespeed_group_cells_match_when_mobile_none(self):
        """If mobile PSI is None but desktop is 90, mobile becomes
        'N/A' and desktop is 90.0 (group consistency: a single None
        yields 'N/A' for that cell; the other keeps its value)."""
        sheet = _build_sheet([SAMPLE_KEYWORDS_RECORDS[0]])
        pagespeed = MagicMock()
        pagespeed.analyze_both.return_value = {"mobile": None, "desktop": 90.0}

        workflow = WebsiteInsightsWorkflow(
            sheet=sheet, pagespeed=pagespeed, gsc=None
        )
        output = workflow.run()
        row = output[1]
        assert row[1] == "N/A"
        assert row[2] == "90.0"


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------
class TestUrlMatching:
    def test_url_matching_integration(self):
        target = "https://www.target-site.com/products"
        assert exact_url_match(target, SAMPLE_SERP_RESPONSE["organic_results"][2]["link"])

    def test_url_not_found(self):
        target = "https://nonexistent.com/page"
        assert not any(
            exact_url_match(target, r["link"])
            for r in SAMPLE_SERP_RESPONSE["organic_results"]
        )


# ---------------------------------------------------------------------------
# Location map
# ---------------------------------------------------------------------------
class TestLocationMap:
    def test_normalize_known_city(self):
        assert normalize_location("Mumbai") == "Mumbai, Maharashtra, India"

    def test_normalize_case_insensitive(self):
        assert normalize_location("mumbai") == "Mumbai, Maharashtra, India"

    def test_normalize_unknown_city_appends_india(self):
        assert normalize_location("Kerala") == "Kerala, India"

    def test_normalize_empty_returns_india(self):
        assert normalize_location("") == "India"

    def test_normalize_whitespace_only_returns_india(self):
        assert normalize_location("   ") == "India"
