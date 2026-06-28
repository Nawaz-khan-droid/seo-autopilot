from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from modules.serp_client import SerpApiError, SerpClient


class TestSerpClientInit:
    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="SERPAPI_KEY is required"):
            SerpClient(api_key="")

    def test_accepts_valid_key(self):
        client = SerpClient(api_key="test_key_123")
        assert client.api_key == "test_key_123"


class TestSerpClientSearch:
    def setup_method(self):
        self.client = SerpClient(api_key="valid_key")

    @patch("modules.serp_client.requests.get")
    def test_successful_search(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "organic_results": [
                {"position": 1, "link": "https://example.com"}
            ]
        }

        result = self.client.search(
            keyword="test query",
            location="Mumbai, India",
            device="desktop",
        )
        assert "organic_results" in result
        assert len(result["organic_results"]) == 1

    @patch("modules.serp_client.requests.get")
    def test_http_error_raises(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("connection failed")

        with pytest.raises(requests.ConnectionError):
            self.client.search("test", "India")

    @patch("modules.serp_client.requests.get")
    def test_api_error_in_response(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "error": "Invalid API key"
        }

        with pytest.raises(SerpApiError, match="Invalid API key"):
            self.client.search("test", "India")

    @patch("modules.serp_client.requests.get")
    def test_empty_organic_results(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {}

        result = self.client.search("test", "India")
        assert result.get("organic_results", []) == []
