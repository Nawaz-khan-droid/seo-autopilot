"""Lightweight multi-provider rank fallback for single keyword lookups.

Tries configured SERP providers in order until one finds the target URL.
Shared between:
- ``api/parallel_fetch._fetch_rankings_via_serp`` (audit pipeline)
- ``orchestrator/serp_snapshot.SerpSnapshotWorkflow`` (sheet-based tracking)

BrowserOS is excluded — it requires Playwright CDP and is too heavy for
a single keyword lookup. Use ``SerpSnapshotWorkflow`` if BrowserOS is needed.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from config.serp_config import RANK_PROVIDERS, provider_display_name
from modules.url_utils import exact_url_match

logger = logging.getLogger(__name__)

_LIGHTWEIGHT_PROVIDERS = {"serpapi", "searchapi", "apify"}


def _client_available(provider: str) -> bool:
    if provider == "serpapi":
        return bool(os.environ.get("SERPAPI_KEY"))
    if provider == "searchapi":
        return bool(os.environ.get("SEARCHAPI_API_KEY"))
    if provider == "apify":
        return bool(os.environ.get("APIFY_API_KEY"))
    return False


def any_provider_available() -> bool:
    """Check if any SERP provider is configured. Used to skip rank checks early."""
    return any(_client_available(p) for p in _LIGHTWEIGHT_PROVIDERS)


def _search_single(
    provider: str, keyword: str, location: str, device: str,
) -> dict[str, Any] | None:
    """Call a single provider's search method. Returns parsed response or None."""
    try:
        if provider == "serpapi":
            api_key = os.environ.get("SERPAPI_KEY", "")
            if not api_key:
                return None
            from modules.serp_client import SerpClient
            return SerpClient(api_key=api_key, max_depth=30).search(
                keyword=keyword, location=location, device=device,
            )

        if provider == "searchapi":
            api_key = os.environ.get("SEARCHAPI_API_KEY", "")
            if not api_key:
                return None
            from modules.searchapi_client import SearchApiClient
            return SearchApiClient(api_key=api_key).search(
                keyword=keyword, location=location,
            )

        if provider == "apify":
            api_key = os.environ.get("APIFY_API_KEY", "")
            if not api_key:
                return None
            from modules.apify_client import ApifyClient
            return ApifyClient(api_key=api_key).search(
                keyword=keyword, location=location, device=device,
                pages=3, results_per_page=10,
            )
    except Exception as e:
        logger.debug("Provider %s failed for '%s': %s", provider, keyword, e)
    return None


def try_providers(
    keyword: str,
    target_url: str,
    location: str = "India",
    device: str = "desktop",
    provider_order: list[str] | None = None,
) -> tuple[int | str | None, str | None, str | None]:
    """Try rank providers in order until one finds the target URL.

    Returns ``(position, ranking_url, provider_name)`` on first match,
    or ``(None, None, None)`` if no provider found the target.
    """
    order = [
        p for p in (provider_order or RANK_PROVIDERS)
        if p in _LIGHTWEIGHT_PROVIDERS and _client_available(p)
    ]
    if not order:
        return None, None, None

    for provider in order:
        data = _search_single(provider, keyword, location, device)
        if data is None:
            continue
        for result in data.get("organic_results", []):
            link = str(result.get("link", "") or "")
            if link and exact_url_match(target_url, link):
                pos = result.get("position")
                logger.info(
                    "Rank: '%s' @ #%s via %s",
                    keyword, pos, provider_display_name(provider),
                )
                return pos, link, provider
    return None, None, None
