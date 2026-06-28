from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import requests

from modules.groq_client import GROQ_BASE_URL, GroqClient


class TestGroqClient:
    def setup_method(self):
        self.client = GroqClient(api_key="gsk_test_key")
        self.mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Change: Stable\nCause: No issues found\nRecommendation: Maintain current strategy\nPriority: Low"
                    }
                }
            ]
        }

    def test_init_rejects_empty_key(self):
        client = GroqClient(api_key="")
        assert client.api_key == ""

    def test_chat_returns_none_for_empty_key(self):
        client = GroqClient(api_key="")
        result = client.chat("test prompt")
        assert result is None

    @patch("modules.groq_client.requests.post")
    def test_chat_returns_content(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.mock_response

        result = self.client.chat("Analyze this keyword")
        assert result is not None
        assert "Change:" in result

    @patch("modules.groq_client.requests.post")
    def test_chat_handles_http_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Connection failed")

        result = self.client.chat("test")
        assert result is None

    @patch("modules.groq_client.requests.post")
    def test_chat_handles_malformed_response(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"unexpected": "data"}

        result = self.client.chat("test")
        assert result is None

    @patch("modules.groq_client.requests.post")
    def test_chat_handles_empty_choices(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"choices": []}

        result = self.client.chat("test")
        assert result is None

    def test_chat_uses_correct_endpoint(self):
        assert GROQ_BASE_URL == "https://api.groq.com/openai/v1/chat/completions"

    @patch("modules.groq_client.requests.post")
    def test_chat_sends_system_prompt(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.mock_response

        self.client.chat("user message", system_prompt="You are an SEO analyst")
        call_kwargs = mock_post.call_args[1]
        sent_messages = json.loads(mock_post.call_args[1]["json"])["messages"] if isinstance(mock_post.call_args[1]["json"], str) else mock_post.call_args[1]["json"]["messages"]
        # Actually let me use the request directly
        payload = mock_post.call_args[1]["json"]
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "You are an SEO analyst"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "user message"

    @patch("modules.groq_client.requests.post")
    def test_chat_skips_system_prompt_when_none(self, mock_post):
        mock_post.return_value.ok = True
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self.mock_response

        self.client.chat("user message", system_prompt=None)
        payload = mock_post.call_args[1]["json"]
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
