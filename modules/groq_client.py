from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama3-70b-8192"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 300


class GroqClient:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.api_key = api_key
        self.model = model

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(
            (requests.ConnectionError, requests.Timeout)
        ),
    )
    def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str | None:
        if not self.api_key:
            logger.warning("Groq: no API key configured")
            return None

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        logger.info(
            f"Groq request: model={self.model} "
            f"prompt_chars={len(prompt)} "
            f"system_chars={len(system_prompt) if system_prompt else 0} "
            f"max_tokens={max_tokens} temp={temperature}"
        )

        try:
            response = requests.post(
                GROQ_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Groq: HTTP error — {e}", exc_info=True)
            return None

        try:
            content = data["choices"][0]["message"]["content"].strip()
            logger.info(
                f"Groq response: model={self.model} "
                f"response_chars={len(content)} "
                f"finish_reason={data['choices'][0].get('finish_reason', '?')} "
                f"first_120={content[:120]!r}"
            )
            return content
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Groq: unexpected response shape — {e}")
            return None
