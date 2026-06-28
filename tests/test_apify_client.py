"""Unit tests for the Apify client.

These tests use MagicMock for the underlying apify_client (the
third-party library) to avoid making real HTTP calls.
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from modules.apify_client import ApifyClient, ApifyError


# ---------------------------------------------------------------------------
# _parse_item — pure function, no I/O
# ---------------------------------------------------------------------------
class TestParseItem:
    def test_parses_organic_results(self):
        item = {
            "organicResults": [
                {"position": 1, "url": "https://a.com/p", "title": "A"},
                {"position": 2, "url": "https://b.com/p", "title": "B"},
                {"position": 3, "url": "", "title": "C"},  # skipped
            ],
            "aiOverview": {
                "content": "AI summary",
                "sources": [{"url": "https://a.com/p", "title": "A"}],
            },
            "peopleAlsoAsk": [
                {"question": "Q1", "answer": "A1", "url": "https://a.com/p"},
            ],
        }
        result = ApifyClient._parse_item(item)
        assert len(result["organic_results"]) == 2
        assert result["organic_results"][0]["link"] == "https://a.com/p"
        assert result["ai_overview"]["content"] == "AI summary"
        assert len(result["ai_overview"]["sources"]) == 1
        assert result["people_also_ask"][0]["question"] == "Q1"

    def test_ai_overview_none_when_absent(self):
        item = {
            "organicResults": [],
            "peopleAlsoAsk": [],
        }
        result = ApifyClient._parse_item(item)
        assert result["ai_overview"] is None
        assert result["people_also_ask"] == []

    def test_paa_empty_when_absent(self):
        item = {
            "organicResults": [{"position": 1, "url": "https://a.com/p", "title": "A"}],
            "aiOverview": None,
        }
        result = ApifyClient._parse_item(item)
        assert result["people_also_ask"] == []

    def test_paa_non_list_yields_empty(self):
        item = {
            "organicResults": [],
            "aiOverview": None,
            "peopleAlsoAsk": "not a list",
        }
        result = ApifyClient._parse_item(item)
        assert result["people_also_ask"] == []

    def test_no_fabricated_local_maps_or_paid_ads(self):
        """The actor does not return local_maps or paid_ads. Verify
        the parsed result does not fabricate these fields."""
        item = {
            "organicResults": [],
            "peopleAlsoAsk": [],
        }
        result = ApifyClient._parse_item(item)
        assert "local_maps" not in result
        assert "paid_ads" not in result

    def test_organic_skips_empty_url(self):
        item = {
            "organicResults": [
                {"position": 1, "url": "", "title": "x"},
                {"position": 2, "url": "https://a.com", "title": "A"},
            ],
        }
        result = ApifyClient._parse_item(item)
        assert len(result["organic_results"]) == 1
        assert result["organic_results"][0]["link"] == "https://a.com"


# ---------------------------------------------------------------------------
# search_batch
# ---------------------------------------------------------------------------
class TestSearchBatch:
    def _client_with_mock(self, run_return, items):
        client = ApifyClient(api_key="test-key")
        mock_apify = MagicMock()
        mock_actor = MagicMock()
        mock_actor.call.return_value = run_return
        mock_dataset = MagicMock()
        mock_dataset.list_items.return_value.items = items
        mock_apify.actor.return_value = mock_actor
        mock_apify.dataset.return_value = mock_dataset
        client._client = mock_apify
        return client

    def test_returns_mapping_for_each_keyword(self):
        items = [
            {
                "searchQuery": {"term": "seo services mumbai"},
                "organicResults": [
                    {"position": 1, "url": "https://a.com", "title": "A"}
                ],
                "peopleAlsoAsk": [],
            },
        ]
        client = self._client_with_mock(MagicMock(default_dataset_id="d1"), items)
        result = client.search_batch(["seo services mumbai"])
        assert "seo services mumbai" in result
        assert len(result["seo services mumbai"]["organic_results"]) == 1

    def test_missing_keyword_filled_with_empty_response(self):
        client = self._client_with_mock(MagicMock(default_dataset_id="d1"), [])
        result = client.search_batch(["kw1", "kw2"])
        assert result["kw1"] == {
            "organic_results": [], "ai_overview": None, "people_also_ask": []
        }
        assert result["kw2"] == {
            "organic_results": [], "ai_overview": None, "people_also_ask": []
        }

    def test_empty_keywords_returns_empty_dict(self):
        client = ApifyClient(api_key="test-key")
        assert client.search_batch([]) == {}

    def test_batch_failure_returns_empty_responses(self):
        client = ApifyClient(api_key="test-key")
        mock_apify = MagicMock()
        mock_actor = MagicMock()
        mock_actor.call.side_effect = Exception("Connection timeout")
        mock_apify.actor.return_value = mock_actor
        client._client = mock_apify
        result = client.search_batch(["kw1", "kw2"])
        # Never raises; returns empty responses per keyword
        assert result["kw1"]["organic_results"] == []
        assert result["kw2"]["organic_results"] == []


# ---------------------------------------------------------------------------
# verify_actor
# ---------------------------------------------------------------------------
class TestVerifyActor:
    def test_returns_verified_with_capabilities(self):
        client = ApifyClient(api_key="test-key")
        client.search = MagicMock(return_value={
            "organic_results": [{"position": 1, "link": "https://a.com", "title": "A"}],
            "ai_overview": {"content": "x", "sources": []},
            "people_also_ask": [{"question": "q"}],
        })
        result = client.verify_actor()
        assert result["verified"] is True
        assert result["returns_ai_overview"] is True
        assert result["returns_paa"] is True
        assert result["organic_count"] == 1

    def test_returns_not_verified_on_failure(self):
        client = ApifyClient(api_key="test-key")
        client.search = MagicMock(side_effect=ApifyError("auth failed"))
        result = client.verify_actor()
        assert result["verified"] is False
        assert result["returns_ai_overview"] is False
        assert result["returns_paa"] is False
        assert result["organic_count"] == 0

    def test_returns_capabilities_when_no_features(self):
        client = ApifyClient(api_key="test-key")
        client.search = MagicMock(return_value={
            "organic_results": [{"position": 1, "link": "https://a.com", "title": "A"}],
            "ai_overview": None,
            "people_also_ask": [],
        })
        result = client.verify_actor()
        assert result["verified"] is True
        assert result["returns_ai_overview"] is False
        assert result["returns_paa"] is True  # always a list, even if empty
        assert result["organic_count"] == 1


# ---------------------------------------------------------------------------
# search() — single keyword (with mocked underlying client)
# ---------------------------------------------------------------------------
class TestSearchSingle:
    def test_search_returns_parsed_dict(self):
        client = ApifyClient(api_key="test-key")
        mock_apify = MagicMock()
        mock_run = MagicMock()
        mock_run.default_dataset_id = "ds1"
        mock_apify.actor.return_value.call.return_value = mock_run
        mock_apify.dataset.return_value.list_items.return_value.items = [
            {
                "searchQuery": {"term": "kw"},
                "organicResults": [
                    {"position": 1, "url": "https://a.com", "title": "A"}
                ],
                "aiOverview": None,
                "peopleAlsoAsk": [],
            }
        ]
        client._client = mock_apify

        result = client.search("kw")
        assert len(result["organic_results"]) == 1
        assert result["ai_overview"] is None

    def test_search_empty_response_when_no_items(self):
        client = ApifyClient(api_key="test-key")
        mock_apify = MagicMock()
        mock_run = MagicMock()
        mock_run.default_dataset_id = "ds1"
        mock_apify.actor.return_value.call.return_value = mock_run
        mock_apify.dataset.return_value.list_items.return_value.items = []
        client._client = mock_apify

        result = client.search("kw")
        assert result == {
            "organic_results": [], "ai_overview": None, "people_also_ask": []
        }

    def test_search_raises_apify_error_on_failure(self):
        client = ApifyClient(api_key="test-key")
        mock_apify = MagicMock()
        mock_apify.actor.return_value.call.side_effect = Exception("network fail")
        client._client = mock_apify
        with pytest.raises(ApifyError):
            client.search("kw")
