from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from modules.pagespeed import PageSpeedClient


class TestPageSpeedClient:
    def setup_method(self):
        self.client = PageSpeedClient()

    def test_init_defaults(self):
        assert self.client.api_key == ""
        assert self.client._auth_token is None

    def test_init_with_api_key(self):
        client = PageSpeedClient(api_key="test_key")
        assert client.api_key == "test_key"

    @patch("modules.pagespeed.service_account.Credentials.from_service_account_file")
    def test_init_with_credentials_tries_auth(self, mock_creds_file):
        creds = MagicMock()
        creds.token = "ya29.test-token"
        mock_creds_file.return_value = creds
        client = PageSpeedClient(credentials_path="creds.json")
        assert client._auth_token is not None

    @patch("modules.pagespeed.PageSpeedClient._run_strategy")
    def test_analyze_returns_score(self, mock_run):
        mock_run.return_value = {
            "lighthouseResult": {
                "categories": {
                    "performance": {"score": 0.85}
                }
            }
        }
        score = self.client.analyze("https://example.com", "mobile")
        assert score == 85.0

    @patch("modules.pagespeed.PageSpeedClient._run_strategy")
    def test_analyze_returns_none_on_exception(self, mock_run):
        mock_run.side_effect = requests.ConnectionError("API error")
        score = self.client.analyze("https://example.com", "mobile")
        assert score is None

    @patch("modules.pagespeed.PageSpeedClient._run_strategy")
    def test_analyze_both_returns_dict(self, mock_run):
        mock_run.return_value = {
            "lighthouseResult": {
                "categories": {
                    "performance": {"score": 0.75}
                }
            }
        }
        results = self.client.analyze_both("https://example.com")
        assert "mobile" in results
        assert "desktop" in results
        assert results["mobile"] == 75.0
        assert results["desktop"] == 75.0

    @patch("modules.pagespeed.PageSpeedClient._run_strategy")
    def test_missing_score_in_response(self, mock_run):
        mock_run.return_value = {"lighthouseResult": {"categories": {}}}
        score = self.client.analyze("https://example.com", "mobile")
        assert score is None

    @patch("modules.pagespeed.PageSpeedClient._run_strategy")
    def test_missing_lighthouse_result(self, mock_run):
        mock_run.return_value = {}
        score = self.client.analyze("https://example.com", "mobile")
        assert score is None

    @patch("modules.pagespeed.requests.get")
    def test_run_strategy_passes_api_key(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"lighthouseResult": {"categories": {"performance": {"score": 0.8}}}}
        client = PageSpeedClient(api_key="my-api-key")
        client.analyze("https://example.com")
        _, kwargs = mock_get.call_args
        assert "key" in kwargs["params"]
        assert kwargs["params"]["key"] == "my-api-key"

    @patch("modules.pagespeed.requests.get")
    def test_run_strategy_passes_bearer_token(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"lighthouseResult": {"categories": {"performance": {"score": 0.8}}}}
        client = PageSpeedClient()
        client._auth_token = "ya29.test-token"
        client.analyze("https://example.com")
        _, kwargs = mock_get.call_args
        assert "Authorization" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] == "Bearer ya29.test-token"
        assert "key" not in kwargs.get("params", {})

    @patch("modules.pagespeed.requests.get")
    def test_429_retries_with_retry_after(self, mock_get):
        responses = [
            MagicMock(status_code=429, headers={"Retry-After": "1"}, ok=False, raise_for_status=MagicMock(side_effect=requests.HTTPError("429"))),
            MagicMock(status_code=200, ok=True, json=MagicMock(return_value={"lighthouseResult": {"categories": {"performance": {"score": 0.5}}}})),
        ]
        mock_get.side_effect = responses
        client = PageSpeedClient()
        with patch("modules.pagespeed.time.sleep"):
            score = client.analyze("https://example.com")
        assert mock_get.call_count == 2
        assert score == 50.0

    @patch("modules.pagespeed.requests.get")
    def test_429_without_retry_after_uses_default(self, mock_get):
        responses = [
            MagicMock(status_code=429, headers={}, ok=False, raise_for_status=MagicMock(side_effect=requests.HTTPError("429"))),
            MagicMock(status_code=200, ok=True, json=MagicMock(return_value={"lighthouseResult": {"categories": {"performance": {"score": 0.5}}}})),
        ]
        mock_get.side_effect = responses
        client = PageSpeedClient()
        with patch("modules.pagespeed.time.sleep"):
            score = client.analyze("https://example.com")
        assert score == 50.0
