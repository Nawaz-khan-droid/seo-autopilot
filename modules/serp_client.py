"""SerpApi client with pagination support."""
from __future__ import annotations

import logging
from typing import Any

from httpx import HTTPStatusError, RequestError

from modules.http_pool import sync_client
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)

SERPAPI_BASE_URL = "https://serpapi.com/search"
RESULTS_PER_PAGE = 10  # SerpApi returns ~10 organic results per request


class SerpApiError(RuntimeError):
    pass


class SerpClient:
    MAX_DEPTH = 200  # Hard upper bound (~20 API pages per keyword)

    def __init__(self, api_key: str, max_depth: int = 200) -> None:
        if not api_key:
            raise ValueError("SERPAPI_KEY is required")
        self.api_key = api_key
        self.max_depth = min(max_depth, self.MAX_DEPTH)

    def _request_page(
        self, keyword: str, location: str, device: str,
        start: int = 0,
    ) -> dict[str, Any]:
        """Fetch a single page of results from SerpApi."""
        params: dict[str, Any] = {
            "engine": "google",
            "q": keyword,
            "location": location,
            "device": device,
            "api_key": self.api_key,
            "num": RESULTS_PER_PAGE,
            "start": start,
            "gl": "in",
            "hl": "en",
        }
        client = sync_client()
        response = client.get(SERPAPI_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise SerpApiError(data["error"])
        return data

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (RequestError, HTTPStatusError)
        ),
        reraise=True,
    )
    def search(
        self,
        keyword: str,
        location: str,
        device: str = "desktop",
        depth: int = 30,
    ) -> dict[str, Any]:
        """Fetch organic results with pagination.

        `depth` controls how many result positions to collect
        (default 30). Each SerpApi request returns ~10 results.
        The function fetches ceil(depth / 10) pages and merges
        them into a single response dict.

        Clamped to ``self.max_depth`` (default 200).
        """
        depth = min(depth, self.max_depth)
        max_pages = max(1, (depth + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
        all_organic: list[dict[str, Any]] = []
        features: dict[str, Any] = {}

        for page in range(max_pages):
            start = page * RESULTS_PER_PAGE
            try:
                data = self._request_page(keyword, location, device, start=start)
            except Exception as e:
                if page == 0:
                    raise
                # On subsequent pages: partial results are better
                # than failing the whole request.
                logger.warning(
                    f"SerpApi page {page + 1} failed for '{keyword}': "
                    f"{e} — using {len(all_organic)} merged results"
                )
                break

            organic = data.get("organic_results", [])
            # Adjust positions to be absolute (not page-relative)
            for result in organic:
                if "position" in result:
                    result["position"] = (result["position"] or 0) + start

            all_organic.extend(organic)

            # Collect features only from page 1
            if page == 0:
                for key in ("ai_overview", "people_also_ask"):
                    if key in data:
                        features[key] = data[key]

            # If we got fewer results than the page max on a subsequent
            # page, we've hit the last available page — stop early.
            # Page 0 may return fewer than 10 (local pack / featured
            # snippet consumed a slot) but later pages still exist.
            if page > 0 and len(organic) < RESULTS_PER_PAGE:
                break

        # Dedup by link (unlikely but guard against edge cases)
        seen_links: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for result in all_organic:
            link = (result.get("link") or "").strip()
            if link and link not in seen_links:
                seen_links.add(link)
                deduped.append(result)

        result: dict[str, Any] = {"organic_results": deduped}
        if features:
            result.update(features)

        logger.info(
            f"SerpApi: '{keyword}' @ '{location}' ({device}) "
            f"-> {len(deduped)} organic results over {page + 1} page(s)"
        )
        return result
