from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class ApifyError(RuntimeError):
    """Raised for any non-recoverable Apify error (auth, quota, payload)."""


class ApifyClient:
    """Apify google-search-scraper client.

    Capabilities verified by live probe (2026-06-06):
    - organicResults: present, up to 30 entries across 3 pages
    - aiOverview: conditional (only on queries that trigger Google AI Overview)
    - peopleAlsoAsk: always present, may be empty
    - paidResults / paidProducts: always present, always empty for these queries
    - localMap / localMaps / localResults: NOT in payload

    The client exposes:
    - search(): returns organic_results + ai_overview + people_also_ask
    - verify_actor(): one-time startup probe
    - search_batch(): single batch call returning keyword -> result dict
    """

    ACTOR_ID = "apify/google-search-scraper"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("APIFY_API_KEY is required")
        self.api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from apify_client import ApifyClient as _ApifyClient
            self._client = _ApifyClient(token=self.api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type(
            (ConnectionError, TimeoutError)
        ),
        reraise=True,
    )
    def search(
        self,
        keyword: str,
        location: str = "",
        device: str = "desktop",
        pages: int = 1,
        results_per_page: int = 10,
    ) -> dict[str, Any]:
        """Query Apify for a single keyword. Returns the parsed item dict.

        The dict has shape:
            {
                "organic_results": [{"position": int, "link": str, "title": str}, ...],
                "ai_overview": dict | None,
                "people_also_ask": [{"question": str, "answer": str|None, "url": str|None}, ...],
            }
        """
        client = self._get_client()

        country_code = "in"
        if "india" in location.lower():
            country_code = "in"

        actor_input: dict[str, Any] = {
            "queries": keyword,
            "device": "DESKTOP" if device.lower() == "desktop" else "MOBILE",
            "maxPagesPerQuery": pages,
            "resultsPerPage": results_per_page,
            "countryCode": country_code,
            "languageCode": "en",
            "includeAiOverview": True,
        }

        try:
            run = client.actor(self.ACTOR_ID).call(
                run_input=actor_input, wait_duration=timedelta(seconds=120)
            )
            if run is None:
                logger.warning(f"Apify: call returned None for '{keyword}'")
                return self._empty_response()
            dataset_id = run.default_dataset_id
            items = client.dataset(dataset_id).list_items().items
        except Exception as e:
            logger.error(f"Apify search error for '{keyword}': {e}")
            raise ApifyError(str(e)) from e

        if not items:
            logger.warning(f"Apify: no items returned for '{keyword}'")
            return self._empty_response()

        item = items[0]
        return self._parse_item(item)

    def search_batch(
        self,
        keywords: list[str],
        location: str = "",
        device: str = "desktop",
        pages: int = 1,
        results_per_page: int = 10,
    ) -> dict[str, dict[str, Any]]:
        """Single batch call. Returns {keyword_lower: parsed_item_dict}.

        Never raises. Failures for individual keywords are mapped to
        empty responses so the caller can still proceed.

        The Apify actor accepts a newline-joined `queries` string, so
        multiple keywords share one HTTP call (cost ~$0.006 per run
        regardless of keyword count).
        """
        if not keywords:
            return {}
        joined = "\n".join(keywords)
        try:
            client = self._get_client()
            country_code = "in"
            if "india" in location.lower():
                country_code = "in"
            actor_input: dict[str, Any] = {
                "queries": joined,
                "device": "DESKTOP" if device.lower() == "desktop" else "MOBILE",
                "maxPagesPerQuery": pages,
                "resultsPerPage": results_per_page,
                "countryCode": country_code,
                "languageCode": "en",
                "includeAiOverview": True,
            }
            run = client.actor(self.ACTOR_ID).call(
                run_input=actor_input, wait_duration=timedelta(seconds=180)
            )
            if run is None:
                logger.warning("Apify batch: call returned None")
                return {kw.strip().lower(): self._empty_response() for kw in keywords}
            items = client.dataset(run.default_dataset_id).list_items().items
        except Exception as e:
            logger.warning(f"Apify batch failed: {e}")
            return {kw.strip().lower(): self._empty_response() for kw in keywords}

        result: dict[str, dict[str, Any]] = {}
        for item in items:
            term = str(item.get("searchQuery", {}).get("term", "")).strip().lower()
            if term:
                result[term] = self._parse_item(item)

        # Ensure every requested keyword has a result, even if empty
        for kw in keywords:
            k = kw.strip().lower()
            if k not in result:
                result[k] = self._empty_response()

        return result

    def verify_actor(self) -> dict[str, Any]:
        """One-time startup probe. Inspects a single-keyword response to
        confirm which feature fields the actor actually returns.

        Returns:
            {
                "verified": bool,
                "returns_ai_overview": bool,
                "returns_paa": bool,
                "organic_count": int,
            }
        """
        probe_keyword = "seo services mumbai"
        try:
            data = self.search(
                probe_keyword, pages=1, results_per_page=10
            )
            return {
                "verified": True,
                "returns_ai_overview": data.get("ai_overview") is not None,
                "returns_paa": isinstance(data.get("people_also_ask"), list),
                "organic_count": len(data.get("organic_results", [])),
            }
        except Exception as e:
            logger.warning(f"Apify verify_actor failed: {e}")
            return {
                "verified": False,
                "returns_ai_overview": False,
                "returns_paa": False,
                "organic_count": 0,
            }

    def _empty_response(self) -> dict[str, Any]:
        return {
            "organic_results": [],
            "ai_overview": None,
            "people_also_ask": [],
        }

    @staticmethod
    def _parse_item(item: dict[str, Any]) -> dict[str, Any]:
        organic: list[dict[str, Any]] = []
        for r in item.get("organicResults", []):
            url = r.get("url", "")
            if not url:
                continue
            organic.append({
                "position": r.get("position", 0),
                "link": url,
                "title": r.get("title", ""),
            })

        ai_overview = item.get("aiOverview")
        if ai_overview is not None and isinstance(ai_overview, dict):
            ai_overview = {
                "content": ai_overview.get("content", ""),
                "sources": ai_overview.get("sources", []),
            }
        else:
            ai_overview = None

        paa = item.get("peopleAlsoAsk", [])
        if isinstance(paa, list):
            people_also_ask = [
                {
                    "question": p.get("question", ""),
                    "answer": p.get("answer", ""),
                    "url": p.get("url", ""),
                    "title": p.get("title", ""),
                }
                for p in paa
            ]
        else:
            people_also_ask = []

        return {
            "organic_results": organic,
            "ai_overview": ai_overview,
            "people_also_ask": people_also_ask,
        }
