"""Tests for BrowserOSClient — CDP-based Playwright client.

BrowserOS handles site audits, UX detection, and action plan data.
These tests cover the actual API surface (CDP Playwright), not a
hypothetical REST wrapper.

- Connection lifecycle (CDP connect, stealth init, close)
- Page audit (JS evaluation, issue extraction)
- Performance measurement
- Screenshot capture
- Site crawling (BFS, link discovery, dedup)
- Backlink extraction from third-party tools
- SERP search (multi-page, dedup, CAPTCHA detection)
- Error handling (timeout, connection failure, blocked pages)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from modules.browseros_client import BrowserOSClient


# ── Fixtures ──

@pytest.fixture
def client() -> BrowserOSClient:
    return BrowserOSClient(cdp_url="http://127.0.0.1:9100", use_stealth=False)


@pytest.fixture
def mock_page() -> MagicMock:
    page = MagicMock()
    page.evaluate.return_value = {}
    return page


def _make_mock_playwright(page: MagicMock) -> MagicMock:
    """Create a mock Playwright instance that returns *page* on connect via CDP."""
    pw = MagicMock()
    browser = MagicMock()
    context = MagicMock()
    context.pages = [page]
    context.new_page.return_value = page
    browser.contexts = [context]
    pw.chromium.connect_over_cdp.return_value = browser
    pw.stop.return_value = None
    return pw


def _patch_startable(page: MagicMock):
    """Context-manager helper that patches sync_playwright -> .start() -> mock.

    Usage::

        with _patch_startable(mock_page) as pw:
            # pw is the Playwright mock (chromium, stop, etc.)
            # mock_page is the page mock controlled by the test
            ...
    """
    pw = _make_mock_playwright(page)
    startable = MagicMock()
    startable.start.return_value = pw
    return patch("modules.browseros_client.sync_playwright", return_value=startable)


# ── Connection Lifecycle ──

class TestConnection:
    def test_init_defaults(self):
        c = BrowserOSClient()
        assert c.cdp_url == "http://127.0.0.1:9100"
        assert c.use_stealth is True

    def test_init_custom_url(self):
        c = BrowserOSClient(cdp_url="http://localhost:9222", use_stealth=False)
        assert c.cdp_url == "http://localhost:9222"
        assert c.use_stealth is False
        assert c._connected is False

    def test_ensure_connected_success(self, client: BrowserOSClient, mock_page: MagicMock):
        pw = _make_mock_playwright(mock_page)
        startable = MagicMock()
        startable.start.return_value = pw
        with patch("modules.browseros_client.sync_playwright", return_value=startable):
            result = client._ensure_connected()
        assert result is not None
        assert client._connected is True
        pw.chromium.connect_over_cdp.assert_called_once_with(client.cdp_url)

    def test_ensure_connected_reuses(self, client: BrowserOSClient, mock_page: MagicMock):
        pw = _make_mock_playwright(mock_page)
        startable = MagicMock()
        startable.start.return_value = pw
        with patch("modules.browseros_client.sync_playwright", return_value=startable):
            client._ensure_connected()
            pw.chromium.connect_over_cdp.assert_called_once()
            # Second call should reuse without reconnecting
            client._ensure_connected()
            pw.chromium.connect_over_cdp.assert_called_once()

    def test_ensure_connected_playwright_failure(self, client: BrowserOSClient):
        with patch("modules.browseros_client.sync_playwright", side_effect=RuntimeError("no pw")):
            result = client._ensure_connected()
        assert result is None
        assert client._connected is False

    def test_ensure_connected_cdp_failure(self, client: BrowserOSClient):
        startable = MagicMock()
        pw = MagicMock()
        pw.chromium.connect_over_cdp.side_effect = Exception("refused")
        startable.start.return_value = pw
        with patch("modules.browseros_client.sync_playwright", return_value=startable):
            result = client._ensure_connected()
        assert result is None
        assert client._connected is False

    def test_close(self, client: BrowserOSClient, mock_page: MagicMock):
        pw = _make_mock_playwright(mock_page)
        startable = MagicMock()
        startable.start.return_value = pw
        with patch("modules.browseros_client.sync_playwright", return_value=startable):
            client._ensure_connected()
            client.close()
        assert client._page is None
        assert client._context is None
        pw.stop.assert_called_once()


# ── Page Audit ──

class TestPageAudit:
    def test_audit_page_not_connected_returns_error(self, client: BrowserOSClient):
        result = client.audit_page("https://example.com")
        assert result["audit_ok"] is False
        assert "browseros_not_connected" in result["issues"]

    def test_audit_page_success(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = {
            "title": "Test Page", "metaDescription": "A test page",
            "h1": "Welcome", "h2s": ["Section 1"],
            "headingCounts": {"h1": 1, "h2": 1},
            "totalImages": 5, "imagesWithoutAlt": 2,
            "totalLinks": 10, "linkUrls": ["https://example.com/page2"],
            "issues": ["Missing meta description"], "wordCount": 300,
        }
        with _patch_startable(mock_page) as ctx:
            result = client.audit_page("https://example.com")

        assert result["audit_ok"] is True
        assert result["title"] == "Test Page"
        assert result["h1"] == "Welcome"
        assert result["totalImages"] == 5

    def test_audit_page_goto_failure(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.goto.side_effect = Exception("timeout")
        with _patch_startable(mock_page):
            result = client.audit_page("https://slow-site.com")
        assert result["audit_ok"] is False
        assert "page_load_failed" in result["issues"]

    def test_audit_page_detects_missing_h1(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = {
            "title": "No H1 Page", "metaDescription": "desc", "h1": "",
            "h2s": [], "headingCounts": {"h1": 0, "h2": 0},
            "totalImages": 0, "imagesWithoutAlt": 0, "totalLinks": 0,
            "linkUrls": [], "issues": ["Missing h1"], "wordCount": 100,
        }
        with _patch_startable(mock_page):
            result = client.audit_page("https://example.com")
        assert "Missing h1" in result["issues"]

    def test_audit_page_counts_images_without_alt(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = {
            "title": "Image Test", "metaDescription": "", "h1": "H1",
            "h2s": [], "headingCounts": {"h1": 1},
            "totalImages": 10, "imagesWithoutAlt": 3,
            "totalLinks": 0, "linkUrls": [], "issues": [], "wordCount": 50,
        }
        with _patch_startable(mock_page):
            result = client.audit_page("https://example.com")
        assert result["imagesWithoutAlt"] == 3


# ── Performance Measurement ──

class TestPerformance:
    def test_measure_performance_not_connected(self, client: BrowserOSClient):
        result = client.measure_performance("https://example.com")
        assert result["error"] == "browseros_not_connected"

    def test_measure_performance_success(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = {
            "domContentLoaded": 1200, "loadEventEnd": 2400,
            "firstPaint": 800, "firstContentfulPaint": 900,
            "transferSize": 45000, "decodedBodySize": 38000,
            "encodedBodySize": 15000, "domInteractive": None,
            "responseStart": None, "responseEnd": None,
        }
        with _patch_startable(mock_page):
            result = client.measure_performance("https://example.com")

        assert "error" not in result
        assert result["domContentLoaded"] == 1200
        assert result["firstContentfulPaint"] == 900
        assert result["transferSize"] == 45000

    def test_summarize_performance_fast(self):
        c = BrowserOSClient()
        summary = c.summarize_performance({"url": "https://ex.com", "loadEventEnd": 1500, "firstContentfulPaint": 1000})
        assert "fast" in summary["loadTime"]
        assert summary["loadRating"] == "good"

    def test_summarize_performance_slow(self):
        c = BrowserOSClient()
        summary = c.summarize_performance({"url": "https://slow.com", "loadEventEnd": 5000, "firstContentfulPaint": 3500})
        assert "slow" in summary["loadTime"]
        assert summary["loadRating"] == "poor"

    def test_summarize_performance_no_data(self):
        c = BrowserOSClient()
        summary = c.summarize_performance({"url": "https://ex.com"})
        assert summary["loadTime"] == "N/A"


# ── Screenshot Capture ──

class TestScreenshots:
    def test_capture_not_connected(self, client: BrowserOSClient):
        result = client.capture_screenshots("https://example.com")
        assert result["desktop_png"] is None
        assert result["mobile_png"] is None

    def test_capture_desktop_only(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.screenshot.return_value = b"desktop_png_bytes"
        with _patch_startable(mock_page) as ctx:
            client._ensure_connected()
            result = client.capture_screenshots("https://example.com")

        assert result["desktop_png"] == b"desktop_png_bytes"
        assert result["mobile_png"] is not None

    def test_capture_mobile(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.screenshot.return_value = b"mobile_png_bytes"
        with _patch_startable(mock_page):
            client._ensure_connected()
            result = client.capture_screenshot_mobile("https://example.com")
        assert result == b"mobile_png_bytes"


# ── Site Crawl ──

class TestSiteCrawl:
    def test_crawl_not_connected(self, client: BrowserOSClient):
        pages = client.crawl_site("https://example.com")
        assert pages == []

    def test_crawl_single_page(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = {
            "title": "Home", "metaDescription": "", "h1": "Home",
            "h2s": [], "headingCounts": {"h1": 1},
            "totalImages": 0, "imagesWithoutAlt": 0,
            "totalLinks": 5, "linkUrls": [],
            "issues": [], "wordCount": 100,
        }
        with _patch_startable(mock_page):
            client._ensure_connected()
            pages = client.crawl_site("https://example.com", max_pages=1)
        assert len(pages) == 1
        assert pages[0]["audit_ok"] is True

    def test_crawl_discovers_internal_links(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = {
            "title": "Home", "metaDescription": "", "h1": "Home",
            "h2s": [], "headingCounts": {"h1": 1},
            "totalImages": 0, "imagesWithoutAlt": 0,
            "totalLinks": 3,
            "linkUrls": ["https://example.com/about", "https://example.com/contact"],
            "issues": [], "wordCount": 100,
        }
        with _patch_startable(mock_page):
            client._ensure_connected()
            pages = client.crawl_site("https://example.com", max_pages=3)
        assert len(pages) >= 1

    def test_crawl_skips_external_links(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = {
            "title": "Home", "metaDescription": "", "h1": "Home",
            "h2s": [], "headingCounts": {"h1": 1},
            "totalImages": 0, "imagesWithoutAlt": 0,
            "totalLinks": 2, "linkUrls": ["https://other-site.com/page"],
            "issues": [], "wordCount": 100,
        }
        with _patch_startable(mock_page):
            client._ensure_connected()
            pages = client.crawl_site("https://example.com", max_pages=3)
        assert len(pages) == 1


# ── SERP Search ──

class TestSerpSearch:
    def test_search_not_connected(self, client: BrowserOSClient):
        result = client.search("test keyword")
        assert result.get("error") == "browseros_not_connected"

    def test_search_returns_organic_results(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.side_effect = [
            False,  # _detect_blocked_js
            [  # _extract_serp_js
                {"link": "https://result1.com", "title": "Result 1"},
                {"link": "https://result2.com", "title": "Result 2"},
            ],
        ]
        with _patch_startable(mock_page):
            client._ensure_connected()
            result = client.search("test keyword", pages=1)

        assert "organic_results" in result
        assert len(result["organic_results"]) == 2

    def test_search_deduplicates_results(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.side_effect = [
            False,
            [
                {"link": "https://result1.com", "title": "Result 1"},
                {"link": "https://result1.com", "title": "Result 1 Dup"},
            ],
        ]
        with _patch_startable(mock_page):
            client._ensure_connected()
            result = client.search("test keyword", pages=1)

        assert len(result["organic_results"]) == 1

    def test_search_handles_captcha(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = True  # blocked
        with _patch_startable(mock_page):
            client._ensure_connected()
            result = client.search("test keyword")
        assert len(result.get("organic_results", [])) == 0


# ── Backlinks ──

class TestBacklinks:
    def test_fetch_backlinks_not_connected(self, client: BrowserOSClient):
        result = client.fetch_backlinks("example.com")
        assert result["status"] == "BROWSEROS_NOT_CONNECTED"

    def test_fetch_backlinks_no_data(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.return_value = {
            "total_backlinks": None, "ref_domains": None,
            "dofollow": None, "nofollow": None, "dr": None,
        }
        with _patch_startable(mock_page):
            client._ensure_connected()
            result = client.fetch_backlinks("example.com")
        assert result["status"] == "NO_DATA_SCRAPED"

    def test_fetch_backlinks_extracts_data(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.evaluate.side_effect = lambda js: (
            {"total_backlinks": "150", "ref_domains": "45", "dr": "35", "_source": "smallseotools"}
            if "total_backlinks" in (js or "") or "querySelector" in (js or "")
            else False
        )
        with _patch_startable(mock_page):
            client._ensure_connected()
            result = client.fetch_backlinks("example.com")
        assert result.get("total_backlinks") == "150"
        assert result.get("ref_domains") == "45"


# ── Error Handling ──

class TestErrorHandling:
    def test_goto_timeout_returns_error(self, client: BrowserOSClient, mock_page: MagicMock):
        mock_page.goto.side_effect = Exception("Navigation timeout")
        with _patch_startable(mock_page):
            client._ensure_connected()
            result = client.audit_page("https://timeout.com")
        assert result["audit_ok"] is False

    def test_close_safe_when_not_connected(self, client: BrowserOSClient):
        client.close()

    def test_close_safe_on_partial_state(self, client: BrowserOSClient):
        client._playwright = MagicMock()
        client.close()


# ── Static / Utility Methods ──

class TestUtilities:
    def test_stealth_init_script_contains_webdriver(self):
        assert "webdriver" in BrowserOSClient._stealth_init_script()

    def test_extract_serp_js_contains_selectors(self):
        js = BrowserOSClient._extract_serp_js()
        assert "yuRUbf" in js and "h3" in js

    def test_detect_blocked_js_detects_captcha(self):
        js = BrowserOSClient._detect_blocked_js().lower()
        assert "captcha" in js and "unusual traffic" in js

    def test_resolve_url_absolute_returns_none(self):
        """_resolve_url intentionally rejects fully-qualified URLs (use as-is)."""
        assert BrowserOSClient._resolve_url("https://example.com/page", "https://example.com") is None

    def test_resolve_url_relative(self):
        assert BrowserOSClient._resolve_url("/about", "https://example.com") == "https://example.com/about"

    def test_resolve_url_scheme_relative(self):
        assert BrowserOSClient._resolve_url("//cdn.example.com/img.png", "https://example.com") == "https://cdn.example.com/img.png"

    def test_resolve_url_empty_returns_none(self):
        assert BrowserOSClient._resolve_url("", "https://example.com") is None

    def test_resolve_url_javascript_returns_none(self):
        assert BrowserOSClient._resolve_url("javascript:void(0)", "https://example.com") is None
