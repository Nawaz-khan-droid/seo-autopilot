"""Provider hierarchy and feature flags for the SERP rank pipeline.

This module is the single source of truth for which providers participate
in rank detection and in which order. Flipping a flag here changes the
runtime behavior — no code change required.

Provider order semantics:
- `rank_providers` is consulted in order for each keyword.
- The first provider that returns a successful result with the target
  URL in the top N organic results wins for that keyword.
- If a provider returns a HARD error (auth/quota/5xx-after-retry),
  the workflow breaker increments; after 3 consecutive hard errors,
  the provider is skipped for the remainder of the run.
- Soft "target not found" is not an error — the next provider is tried.

Feature values:
- Apify is the only feature provider. We surface two features:
  `aiOverview` and `peopleAlsoAsk`.
- Yes / No / N/A semantics:
    YES = block returned AND target appears in it
    NO  = block returned AND target absent
    N/A = block not returned (key absent from payload)
"""
from __future__ import annotations

import logging
import os
from typing import Any

# Provider hierarchy consulted in this order for rank detection.
# Default: SerpApi primary, Apify secondary, BrowserOS tertiary, SearchApi.io quaternary.
# Override via PROVIDER_ORDER env var (comma-separated, e.g. "apify").
VALID_PROVIDERS = {"serpapi", "apify", "browseros", "searchapi"}

_provider_order_env = os.getenv("PROVIDER_ORDER")
if _provider_order_env:
    RANK_PROVIDERS: list[str] = [
        p.strip() for p in _provider_order_env.split(",") if p.strip()
    ]
else:
    RANK_PROVIDERS: list[str] = ["serpapi", "apify", "browseros", "searchapi"]

# Validate: warn on unknown provider names, skip them at runtime
_unknown = [p for p in RANK_PROVIDERS if p not in VALID_PROVIDERS]
if _unknown:
    logger = logging.getLogger(__name__)
    logger.warning(
        f"Unknown provider(s) in PROVIDER_ORDER: {_unknown}. "
        f"Valid providers: {sorted(VALID_PROVIDERS)}"
    )

# Apify-specific behavior. Apify is allowed to participate in rank
# detection when this flag is True. It is allowed to be a feature
# provider unconditionally when APIFY_API_KEY is set.
APIFY_CONFIG: dict[str, Any] = {
    "participate_in_rank_detection": True,
    "max_pages": 3,
    "results_per_page": 10,
}

# Threshold for the per-provider hard-error breaker.
# After this many consecutive hard errors from a single provider,
# that provider is skipped for the rest of the run and a CRITICAL
# log line is emitted.
PROVIDER_BREAKER_THRESHOLD: int = 3

# Feature value sentinels
FEATURE_YES = "YES"
FEATURE_NO = "NO"
FEATURE_NA = "N/A"
FEATURE_VALUES = {FEATURE_YES, FEATURE_NO, FEATURE_NA}


def is_valid_provider(name: str) -> bool:
    return name in {"serpapi", "apify", "browseros", "searchapi"}


def provider_display_name(name: str) -> str:
    return {
        "serpapi": "SerpApi",
        "apify": "Apify",
        "browseros": "BrowserOS",
        "searchapi": "SearchApi.io",
    }.get(name, name)
