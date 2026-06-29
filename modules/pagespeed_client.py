from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from modules.http_pool import sync_client, async_client

logger = logging.getLogger(__name__)

PSI_API = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
PSI_TIMEOUT_S = 45


@dataclass
class PSIResult:
    strategy: str = "mobile"
    score: int | None = None
    lcp_seconds: float | None = None
    inp_ms: int | None = None
    cls_score: float | None = None
    tbt_ms: int | None = None
    fcp_seconds: float | None = None
    ttfb_seconds: float | None = None
    opportunities: list[str] = field(default_factory=list)
    has_field_data: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.score is not None


def _parse(response_data: dict[str, Any], strategy: str) -> PSIResult:
    """Extract Lab + Field metrics from a PSI API response."""
    result = PSIResult(strategy=strategy)
    lhs = response_data.get("lighthouseResult", {})
    audits = lhs.get("audits", {})

    # Performance score (0-100)
    score_frac = lhs.get("categories", {}).get("performance", {}).get("score")
    if score_frac is not None:
        result.score = int(score_frac * 100)

    # --- Lab metrics (Lighthouse simulated) ---
    def _num(key: str) -> float | None:
        node = audits.get(key, {})
        nv = node.get("numericValue")
        return nv if nv is not None and isinstance(nv, (int, float)) else None

    lcp_ms = _num("largest-contentful-paint")
    if lcp_ms is not None:
        result.lcp_seconds = round(lcp_ms / 1000.0, 2)

    cls_raw = _num("cumulative-layout-shift")
    if cls_raw is not None:
        result.cls_score = round(float(cls_raw), 3)

    tbt_raw = _num("total-blocking-time")
    if tbt_raw is not None:
        result.tbt_ms = int(tbt_raw)

    fcp_ms = _num("first-contentful-paint")
    if fcp_ms is not None:
        result.fcp_seconds = round(fcp_ms / 1000.0, 2)

    ttfb_ms = _num("server-response-time")
    if ttfb_ms is not None:
        result.ttfb_seconds = round(ttfb_ms / 1000.0, 2)

    # Opportunities (failed audits)
    for ref in lhs.get("categories", {}).get("performance", {}).get("auditRefs", []):
        aid = ref.get("id", "")
        audit = audits.get(aid, {})
        if audit.get("score", 1) is not None and audit["score"] < 1:
            title = audit.get("title", aid)
            result.opportunities.append(title)
    result.opportunities = result.opportunities[:10]

    # --- Field metrics (CrUX real-user data) ---
    loading_exp = response_data.get("loadingExperience", {})
    metrics = loading_exp.get("metrics", {})
    if metrics:
        result.has_field_data = True
        inp_metric = metrics.get("INTERACTION_TO_NEXT_PAINT", {})
        if inp_metric:
            inp_pct = inp_metric.get("percentile")
            if inp_pct is not None:
                result.inp_ms = int(inp_pct)

    return result


# ---------------------------------------------------------------------------
# Sync API (for synchronous audit pipeline)
# ---------------------------------------------------------------------------
def fetch_pagespeed_metrics(url: str, strategy: str = "mobile") -> dict[str, Any]:
    """Fetch CWV + performance data from PSI API (sync, no key required).
    Uses a single light-weight request — fails fast on rate-limit.

    Returns a dict compatible with the audit_workflow Evidence system:
      {score, lcp_seconds, inp_ms, cls_score, tbt_ms, fcp_seconds, ttfb_seconds,
       opportunities, has_field_data, error}
    """
    # Quick single attempt — if it fails (rate-limited, etc.), return fast
    params = {"url": url, "strategy": strategy.upper(), "category": "PERFORMANCE"}
    try:
        client = sync_client()
        resp = client.get(PSI_API, params=params, timeout=10)
        if resp.status_code == 429:
            return {"strategy": strategy, "error": "rate_limited"}
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        status_code = getattr(e, "response", None) and e.response.status_code
        if status_code:
            return {"strategy": strategy, "error": f"http_{status_code}"}
        return {"strategy": strategy, "error": str(e)}

    # First attempt succeeded — now parse it
    parsed = _parse(data, strategy)
    result = {
        "strategy": strategy,
        "score": parsed.score,
        "lcp_seconds": parsed.lcp_seconds,
        "inp_ms": parsed.inp_ms,
        "cls_score": parsed.cls_score,
        "tbt_ms": parsed.tbt_ms,
        "fcp_seconds": parsed.fcp_seconds,
        "ttfb_seconds": parsed.ttfb_seconds,
        "opportunities": parsed.opportunities,
        "has_field_data": parsed.has_field_data,
        "error": None,
    }
    logger.info(
        "PSI %s: score=%s lcp=%s inp=%s cls=%s field=%s",
        strategy, parsed.score, parsed.lcp_seconds, parsed.inp_ms,
        parsed.cls_score, parsed.has_field_data,
    )
    return result


# ---------------------------------------------------------------------------
# Async API (for FastAPI endpoints, asyncio.gather with link checker)
# ---------------------------------------------------------------------------
async def fetch_pagespeed_metrics_async(url: str, strategy: str = "mobile") -> dict[str, Any]:
    """Async version for use with asyncio.gather()."""
    params = {"url": url, "strategy": strategy.upper(), "category": "PERFORMANCE"}
    try:
        client = async_client()
        resp = await client.get(PSI_API, params=params, timeout=PSI_TIMEOUT_S)
        if resp.status_code == 429:
            return {"strategy": strategy, "error": "rate_limited"}
        resp.raise_for_status()
        data = resp.json()

        parsed = _parse(data, strategy)
        return {
            "strategy": strategy,
            "score": parsed.score,
            "lcp_seconds": parsed.lcp_seconds,
            "inp_ms": parsed.inp_ms,
            "cls_score": parsed.cls_score,
            "tbt_ms": parsed.tbt_ms,
            "fcp_seconds": parsed.fcp_seconds,
            "ttfb_seconds": parsed.ttfb_seconds,
            "opportunities": parsed.opportunities,
            "has_field_data": parsed.has_field_data,
            "error": None,
        }
    except Exception as e:
        logger.warning("PSI async %s failed for %s: %s", strategy, url, e)
        return {"strategy": strategy, "error": str(e)}


async def fetch_both_strategies(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch both mobile and desktop PSI data in parallel.

    Example:
        mobile, desktop = await fetch_both_strategies("https://example.com")
    """
    mobile, desktop = await asyncio.gather(
        fetch_pagespeed_metrics_async(url, "mobile"),
        fetch_pagespeed_metrics_async(url, "desktop"),
    )
    return mobile, desktop
