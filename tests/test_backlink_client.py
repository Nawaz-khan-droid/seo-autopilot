"""Tests for the two-tier backlink pipeline (CSV upload + BrowserOS + graceful fallback)."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures: temp directories and test CSV paths
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_storage():
    """Temporarily redirect STORAGE_DIR to a temp dir."""
    from modules import backlink_client as bc
    orig = bc.STORAGE_DIR
    tmp = Path(tempfile.mkdtemp())
    bc.STORAGE_DIR = tmp
    yield tmp
    bc.STORAGE_DIR = orig
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()


@pytest.fixture
def temp_memories():
    """Temporarily redirect MEMORIES_DIR to a temp dir."""
    from modules import backlink_client as bc
    orig = bc.MEMORIES_DIR
    tmp = Path(tempfile.mkdtemp())
    bc.MEMORIES_DIR = tmp
    yield tmp
    bc.MEMORIES_DIR = orig
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()


# ---------------------------------------------------------------------------
# CSV Header Variant Tests (Tier 1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("csv_text,expected", [
    # Ahrefs-style headers
    ("Total Backlinks,Referring Domains,DoFollow,NoFollow,Domain Rating,Source\n500,120,350,150,45,Ahrefs\n",
     {"total_backlinks": "500", "ref_domains": "120", "dofollow": "350", "nofollow": "150", "dr": "45", "source": "Ahrefs"}),
    # Semrush-style headers
    ("Backlinks,Referring Domains,Followed Links,Not Followed,Authority Score,Tool\n600,200,480,120,52,Semrush\n",
     {"total_backlinks": "600", "ref_domains": "200", "dofollow": "480", "nofollow": "120", "dr": "52", "source": "Semrush"}),
    # Canonical lowercase
    ("total_backlinks,ref_domains,dofollow,nofollow,dr,source\n700,180,550,150,48,Moz\n",
     {"total_backlinks": "700", "ref_domains": "180", "dofollow": "550", "nofollow": "150", "dr": "48", "source": "Moz"}),
    # Mixed short names
    ("Total,Referring Domain,Follow Links,Nofollow Links,DA,Provider\n300,90,250,50,42,Ubersuggest\n",
     {"total_backlinks": "300", "ref_domains": "90", "dofollow": "250", "nofollow": "50", "dr": "42", "source": "Ubersuggest"}),
    # Ahrefs WMT export style
    ("Domain Rating,Backlinks,Referring Domains,Dofollow,Nofollow,Source\n55,800,210,620,180,Ahrefs WMT\n",
     {"total_backlinks": "800", "ref_domains": "210", "dofollow": "620", "nofollow": "180", "dr": "55", "source": "Ahrefs WMT"}),
    # No source column = default "CSV Upload"
    ("total_backlinks,ref_domains\n400,100\n",
     {"total_backlinks": "400", "ref_domains": "100", "source": "CSV Upload"}),
])
def test_csv_various_headers(csv_text, expected, temp_storage, temp_memories):
    from modules.backlink_client import fetch_backlinks

    csv_path = temp_storage / "testdomain.com.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    result = fetch_backlinks("https://testdomain.com")
    assert result["status"] == "AVAILABLE"
    for key, val in expected.items():
        assert result.get(key) == val, f"{key}: expected {val!r}, got {result.get(key)!r}"


# ---------------------------------------------------------------------------
# AWAITING_DATA Fallback Test (Tier 2 fallback)
# ---------------------------------------------------------------------------

def test_no_data_returns_awaiting(temp_storage, temp_memories):
    from modules.backlink_client import fetch_backlinks
    with patch("modules.backlink_client._find_mentions_via_ddg", return_value=None), \
         patch("modules.backlink_client._fetch_openpagerank", return_value=None):
        result = fetch_backlinks("https://unknown-domain-xyz.com")
        assert result["status"] == "AWAITING_DATA"
        assert result["total_backlinks"] == "Data Pending"
        assert result["ref_domains"] == "Data Pending"
        assert result["source"] == "Manual Entry Needed"


# ---------------------------------------------------------------------------
# Cache Tests
# ---------------------------------------------------------------------------

def test_stale_cache_is_skipped(temp_storage, temp_memories):
    from modules.backlink_client import fetch_backlinks

    stale = {
        "domain": "cached.com",
        "status": "AVAILABLE",
        "total_backlinks": "999",
        "ref_domains": "50",
        "source": "Cache",
        "checked_at": (datetime.now() - timedelta(days=30)).isoformat(),
    }
    cache_path = temp_memories / "backlinks_cached.com.json"
    cache_path.write_text(json.dumps(stale), encoding="utf-8")

    with patch("modules.backlink_client._find_mentions_via_ddg", return_value=None), \
         patch("modules.backlink_client._fetch_openpagerank", return_value=None):
        result = fetch_backlinks("https://cached.com")
        assert result["status"] == "AWAITING_DATA"


def test_fresh_cache_is_used(temp_storage, temp_memories):
    from modules.backlink_client import fetch_backlinks

    fresh = {
        "domain": "fresh.com",
        "status": "AVAILABLE",
        "total_backlinks": "250",
        "ref_domains": "60",
        "source": "Cache",
        "checked_at": datetime.now().isoformat(),
    }
    cache_path = temp_memories / "backlinks_fresh.com.json"
    cache_path.write_text(json.dumps(fresh), encoding="utf-8")

    result = fetch_backlinks("https://fresh.com")
    assert result["status"] == "AVAILABLE"
    assert result["total_backlinks"] == "250"


# ---------------------------------------------------------------------------
# CSV takes priority over cache
# ---------------------------------------------------------------------------

def test_csv_overrides_cache(temp_storage, temp_memories):
    from modules.backlink_client import fetch_backlinks

    cached = {
        "domain": "override.com",
        "status": "AVAILABLE",
        "total_backlinks": "100",
        "source": "Old Cache",
        "checked_at": datetime.now().isoformat(),
    }
    cache_path = temp_memories / "backlinks_override.com.json"
    cache_path.write_text(json.dumps(cached), encoding="utf-8")

    csv_path = temp_storage / "override.com.csv"
    csv_path.write_text("total_backlinks,ref_domains,source\n500,200,Fresh CSV\n", encoding="utf-8")

    result = fetch_backlinks("https://override.com")
    assert result["total_backlinks"] == "500"
    assert result["ref_domains"] == "200"
    assert result["source"] == "Fresh CSV"


# ---------------------------------------------------------------------------
# BrowserOS integration tests (Tier 2)
# ---------------------------------------------------------------------------

def test_browseros_fallback_when_not_connected(temp_storage, temp_memories):
    """When BrowserOS is not running, should fall through to AWAITING_DATA."""
    from modules.backlink_client import fetch_backlinks
    with patch("modules.backlink_client._find_mentions_via_ddg", return_value=None), \
         patch("modules.backlink_client._fetch_openpagerank", return_value=None):
        result = fetch_backlinks("https://no-browseros.com")
        assert result["status"] == "AWAITING_DATA"


@patch("modules.backlink_client._try_browseros_scrape")
def test_browseros_returns_data(mock_scrape, temp_storage, temp_memories):
    from modules.backlink_client import fetch_backlinks

    mock_scrape.return_value = {
        "domain": "bro-ready.com",
        "status": "AVAILABLE",
        "total_backlinks": "320",
        "ref_domains": "85",
        "dofollow": "290",
        "nofollow": "30",
        "dr": "42",
        "source": "browseros_scrape",
    }

    result = fetch_backlinks("https://bro-ready.com")
    assert result["status"] == "AVAILABLE"
    assert result["total_backlinks"] == "320"
    assert result["source"] == "browseros_scrape"


# ---------------------------------------------------------------------------
# _close_browser safety test
# ---------------------------------------------------------------------------

def test_close_browser_noop_when_not_initialized():
    """_close_browser should not crash when Playwright was never started."""
    from api.browser_manager import _close_browser, _PLAYWRIGHT_TLS
    if hasattr(_PLAYWRIGHT_TLS, "pw"):
        del _PLAYWRIGHT_TLS.pw
    if hasattr(_PLAYWRIGHT_TLS, "browser"):
        del _PLAYWRIGHT_TLS.browser
    _close_browser()
    assert not hasattr(_PLAYWRIGHT_TLS, "pw") or _PLAYWRIGHT_TLS.pw is None
    assert not hasattr(_PLAYWRIGHT_TLS, "browser") or _PLAYWRIGHT_TLS.browser is None


# ---------------------------------------------------------------------------
# Fetch parallel integration (backlink included)
# ---------------------------------------------------------------------------

@patch("modules.backlink_client.fetch_backlinks")
def test_fetch_parallel_includes_backlinks(mock_fetch):
    from api.parallel_fetch import _fetch_parallel

    mock_fetch.return_value = {
        "status": "AVAILABLE",
        "total_backlinks": "500",
        "ref_domains": "120",
        "source": "CSV Upload",
    }

    with patch("api.parallel_fetch._fetch_gsc_data") as mock_gsc, \
         patch("api.parallel_fetch._fetch_ga4_data") as mock_ga4, \
         patch("modules.pagespeed_client.fetch_pagespeed_metrics") as mock_psi:
        mock_psi.return_value = {"error": "rate_limited"}
        mock_gsc.return_value = {}
        mock_ga4.return_value = {}

        result = _fetch_parallel("https://example.com")
        assert result["backlinks"]["status"] == "AVAILABLE"
        assert result["backlinks"]["total_backlinks"] == "500"


# ---------------------------------------------------------------------------
# BacklinkData facts builder test
# ---------------------------------------------------------------------------

def test_facts_backlinks_awaiting():
    """Verify _build_facts_from_audit sets status=AWAITING_DATA properly."""
    from datetime import datetime
    from api.facts_assembler import _build_facts_from_audit
    from modules.firecrawl_client import CrawlResult

    crawl = CrawlResult()
    facts = _build_facts_from_audit(
        url="https://example.com",
        crawl_result=crawl,
        sheet_data=None,
        report_month="June 2026",
        backlinks_data={"status": "AWAITING_DATA", "domain": "example.com"},
    )
    assert facts.backlinks.status == "AWAITING_DATA"


def test_facts_backlinks_available():
    """Verify _build_facts_from_audit sets status=AVAILABLE and populates fields."""
    from api.facts_assembler import _build_facts_from_audit
    from modules.firecrawl_client import CrawlResult

    crawl = CrawlResult()
    facts = _build_facts_from_audit(
        url="https://example.com",
        crawl_result=crawl,
        sheet_data=None,
        report_month="June 2026",
        backlinks_data={
            "status": "AVAILABLE",
            "total_backlinks": "500",
            "ref_domains": "120",
            "dofollow": "400",
            "nofollow": "100",
            "source": "CSV Upload",
        },
    )
    assert facts.backlinks.status == "AVAILABLE"
    assert facts.backlinks.total_backlinks.value == "500"
    assert facts.backlinks.ref_domains.value == "120"
