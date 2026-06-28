from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from modules.tavily_client import TavilyClient

logger = logging.getLogger(__name__)

MEMORIES_DIR = Path(__file__).resolve().parent.parent / "memories"
MEMORIES_DIR.mkdir(exist_ok=True)

MEMORY_TTL_DAYS = 7


def _domain_from_url(url: str) -> str:
    return (
        url.replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .split("/")[0]
        .split("?")[0]
    )


def _memory_path(domain: str) -> Path:
    return MEMORIES_DIR / f"memory_{domain}.json"


def _known_client_profile(domain: str) -> dict[str, Any] | None:
    """Check if this domain matches a known client in client_context.py."""
    try:
        from report.client_context import CLIENT_PROFILES
        for name, profile in CLIENT_PROFILES.items():
            known_url = (profile.get("website") or "").strip().lower()
            if known_url and _domain_from_url(known_url) == domain:
                return {
                    "domain": domain,
                    "client_name": name.title(),
                    "niche": profile.get("business_type", ""),
                    "business_type": profile.get("business_type", "Unknown"),
                    "source": "client_context.py",
                    "discovered_at": datetime.now().isoformat(timespec="seconds"),
                }
    except Exception:
        pass
    return None


def load_memory(domain: str) -> dict[str, Any] | None:
    """Load cached memory profile for a domain. Returns None if stale/missing."""
    path = _memory_path(domain)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        created = datetime.fromisoformat(data.get("discovered_at", "2000-01-01"))
        if datetime.now() - created > timedelta(days=MEMORY_TTL_DAYS):
            logger.info("Memory for %s is stale (>%d days), will refresh", domain, MEMORY_TTL_DAYS)
            return None
        logger.info("Loaded cached memory for %s", domain)
        return data
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("Failed to load memory for %s: %s", domain, e)
        return None


def save_memory(domain: str, data: dict[str, Any]) -> dict[str, Any]:
    """Save memory profile to disk."""
    data["discovered_at"] = datetime.now().isoformat(timespec="seconds")
    path = _memory_path(domain)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved memory for %s to %s", domain, path.name)
    return data


def get_client_memory(url: str) -> dict[str, Any]:
    """Get or create a client memory profile for a URL.

    Resolution order:
      1. Cached memory_{domain}.json (fresh within TTL)
      2. Known client in client_context.py
      3. Tavily discover (1 API call)
      4. Default fallback

    Returns {domain, client_name, niche, business_type, source, discovered_at}.
    """
    domain = _domain_from_url(url)

    # 1. Check cache
    cached = load_memory(domain)
    if cached:
        return cached

    # 2. Check known client profiles
    known = _known_client_profile(domain)
    if known:
        return save_memory(domain, known)

    # 3. Use Tavily (1 API call)
    tavily = TavilyClient()
    if tavily.available:
        discovered = tavily.discover(url)
        profile = {
            "domain": domain,
            "client_name": domain.split(".")[0].title(),
            "niche": discovered.get("niche", ""),
            "business_type": discovered.get("business_type", "Unknown"),
            "source": "tavily_discover",
        }
        return save_memory(domain, profile)

    # 4. Default fallback
    logger.warning("No memory source available for %s — using defaults", domain)
    return {
        "domain": domain,
        "client_name": domain.split(".")[0].title(),
        "niche": "",
        "business_type": "Unknown",
        "source": "default",
        "discovered_at": datetime.now().isoformat(timespec="seconds"),
    }


def build_context_prompt(memory: dict[str, Any]) -> str:
    """Build a grounded context prompt section from client memory.

    Insert this into LLM system prompts to prevent hallucination.
    """
    lines = ["## CLIENT CONTEXT (verified from external research)"]
    lines.append(f"Client: {memory.get('client_name', memory.get('domain', 'Unknown'))}")

    niche = memory.get("niche", "")
    if niche:
        lines.append(f"Industry/Niche: {niche}")

    biz_type = memory.get("business_type", "")
    if biz_type:
        lines.append(f"Business Model: {biz_type}")

    source = memory.get("source", "unknown")
    lines.append(f"Context Source: {source}")
    lines.append("")
    lines.append("IMPORTANT: Use this context to understand WHO the client is.")
    lines.append("Do NOT invent metrics, traffic, or ranking data from this context.")
    lines.append("All data must come from the evidence layer below.")
    return "\n".join(lines)
