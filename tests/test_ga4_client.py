from __future__ import annotations

from modules.ga4_client import AnalyticsClient


class TestAnalyticsClient:
    def test_disabled_when_no_property_id(self):
        client = AnalyticsClient(
            credentials_path="creds.json", property_id=""
        )
        assert client._enabled is False

    def test_disabled_returns_fallback(self):
        client = AnalyticsClient(
            credentials_path="creds.json", property_id=""
        )
        result = client.get_metrics()
        assert result["organic_users"] == "Access Required"
        assert result["sessions"] == "Access Required"
        assert result["engaged_sessions"] == "Access Required"

    def test_client_not_initialized_returns_fallback(self):
        client = AnalyticsClient(
            credentials_path="creds.json", property_id=""
        )
        client._enabled = True
        client.client = None
        result = client.get_metrics()
        assert result["organic_users"] == "Access Required"

    def test_get_metrics_returns_fallback_on_exception(self):
        client = AnalyticsClient(
            credentials_path="creds.json", property_id="123456"
        )
        client._enabled = True
        client.client = None
        result = client.get_metrics()
        assert result["organic_users"] == "Access Required"
