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

SEARCHAPI_BASE = "https://www.searchapi.io/api/v1/search"


class SearchApiError(RuntimeError):
    pass


class SearchApiClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("SEARCHAPI_API_KEY is required")
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (requests.ConnectionError, requests.Timeout)
        ),
        reraise=True,
    )
    def search(
        self,
        keyword: str,
        location: str = "",
        device: str = "desktop",
        num_results: int = 100,
        page: int = 1,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "engine": "google_rank_tracking",
            "q": keyword,
            "api_key": self.api_key,
            "num": num_results,
            "page": page,
            "gl": "in",
            "hl": "en",
        }
        if device == "mobile":
            params["device"] = "mobile"
        elif device == "tablet":
            params["device"] = "tablet"
        if location:
            params["location"] = location

        try:
            response = requests.get(
                SEARCHAPI_BASE,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(
                f"SearchApi HTTP error for '{keyword}' (page {page}): {e}"
            )
            raise

        if "error" in data:
            error_msg = data["error"]
            logger.error(
                f"SearchApi error for '{keyword}': {error_msg}"
            )
            raise SearchApiError(error_msg)

        organic = data.get("organic_results", [])
        logger.info(
            f"SearchApi.io: '{keyword}' (page {page}, {device}) "
            f"-> {len(organic)} organic results"
        )

        result: dict[str, Any] = {"organic_results": []}
        for item in organic:
            link = item.get("link", "")
            if not link:
                continue
            result["organic_results"].append({
                "position": item.get("position", 0),
                "link": link,
                "title": item.get("title", ""),
            })

        return result
