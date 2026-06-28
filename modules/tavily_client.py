from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

CACHE_TTL_HOURS = 24


class TavilyClient:
    """Efficient Tavily API wrapper with usage limits.

    Two modes — call the appropriate one for the job:
      - discover(url) → {niche, business_type, domain}  1 API call + cache
      - search(query) → raw search results              1 API call

    Guards:
      - Skips API if TAVILY_API_KEY is missing
      - Caches discover results for 24h per domain
      - Raises on credit exhaustion (402)
    """

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("TAVILY_API_KEY", "")
        if not key:
            from pathlib import Path
            dotenv_path = Path(__file__).resolve().parent.parent / ".env"
            if dotenv_path.exists():
                load_dotenv(dotenv_path=str(dotenv_path), override=True)
                key = os.environ.get("TAVILY_API_KEY", "")
        self._key = key
        self._client: Any = None

    @property
    def _inner(self):
        if self._client is None and self._key:
            from tavily import TavilyClient as _TavilyClient
            self._client = _TavilyClient(api_key=self._key)
        return self._client

    @property
    def available(self) -> bool:
        return bool(self._key)

    def discover(self, url: str) -> dict[str, Any]:
        """Discover niche + business type for a URL. Uses 1 API call.

        Returns {domain, niche, business_type} or partial result on error.
        """
        domain = url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].split("?")[0]
        result: dict[str, Any] = {"domain": domain, "niche": "", "business_type": ""}

        if not self._inner:
            logger.warning("Tavily not configured — skipping discover")
            return result

        try:
            query = (
                f"What industry or niche does the website {url} operate in? "
                f"Is it a local business or an e-commerce/global platform? "
                f"Answer concisely."
            )
            search_result = self._inner.search(query=query, search_depth="basic", include_answer=True)
            raw_answer = search_result.get("answer", "") or ""

            # Parse answer into structured fields using a simple heuristic
            raw_lower = raw_answer.lower()
            if "e-commerce" in raw_lower or "ecommerce" in raw_lower or "global" in raw_lower or "online store" in raw_lower:
                result["business_type"] = "E-Commerce/Global"
            elif "local" in raw_lower or "brick" in raw_lower or "physical store" in raw_lower:
                result["business_type"] = "Local"
            else:
                result["business_type"] = "Unknown"

            # Extract niche as the first sentence before a period
            niche = raw_answer.split(".")[0].strip() if raw_answer else ""
            # Remove the query words if they appear
            for prefix in ["this website", "the website", f"{url}"]:
                if niche.lower().startswith(prefix):
                    niche = niche[len(prefix):].strip().lstrip("is ").strip().lstrip("an ").strip().lstrip("a ").strip()
            result["niche"] = niche[:120] if niche else "General Business"

            logger.info("Tavily discover %s → niche=%s type=%s", domain, result["niche"], result["business_type"])
        except Exception as e:
            logger.warning("Tavily discover failed for %s: %s", url, e)

        return result

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """General web search. Use sparingly — each call costs 1 credit.

        Returns list of {title, url, content}.
        """
        if not self._inner:
            logger.warning("Tavily not configured — skipping search")
            return []

        try:
            result = self._inner.search(query=query, search_depth="basic", max_results=max_results)
            items = []
            for r in result.get("results", []):
                items.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": (r.get("content", "") or "")[:500],
                })
            return items
        except Exception as e:
            logger.warning("Tavily search failed: %s", e)
            return []
