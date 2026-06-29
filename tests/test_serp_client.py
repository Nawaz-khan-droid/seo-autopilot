from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

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

    def _mock_sync_client(self, mock_sync_client, json_data=None, side_effect=None, status_code=200):
        mock_client = MagicMock()
        mock_response = MagicMock()
        if side_effect:
            mock_client.get.side_effect = side_effect
        else:
            mock_response.status_code = status_code
            mock_response.json.return_value = json_data or {}
            mock_client.get.return_value = mock_response
        mock_sync_client.return_value = mock_client
        return mock_client

    @patch("modules.serp_client.sync_client")
    def test_successful_search(self, mock_sync_client):
        self._mock_sync_client(mock_sync_client, json_data={
            "organic_results": [
                {"position": 1, "link": "https://example.com"}
            ]
        })

        result = self.client.search(
            keyword="test query",
            location="Mumbai, India",
            device="desktop",
        )
        assert "organic_results" in result
        assert len(result["organic_results"]) == 1

    @patch("modules.serp_client.sync_client")
    def test_http_error_raises(self, mock_sync_client):
        from httpx import HTTPStatusError, RequestError
        mock_client = MagicMock()
        mock_client.get.side_effect = RequestError("connection failed")
        mock_sync_client.return_value = mock_client

        with pytest.raises(RequestError):
            self.client.search("test", "India")

    @patch("modules.serp_client.sync_client")
    def test_api_error_in_response(self, mock_sync_client):
        self._mock_sync_client(mock_sync_client, json_data={
            "error": "Invalid API key"
        })

        with pytest.raises(SerpApiError, match="Invalid API key"):
            self.client.search("test", "India")

    @patch("modules.serp_client.sync_client")
    def test_empty_organic_results(self, mock_sync_client):
        self._mock_sync_client(mock_sync_client, json_data={})

        result = self.client.search("test", "India")
        assert result.get("organic_results", []) == []
