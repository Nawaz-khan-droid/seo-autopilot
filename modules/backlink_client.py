from __future__ import annotations

import csv
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage" / "backlinks"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

MEMORIES_DIR = Path(__file__).resolve().parent.parent / "memories"
MEMORIES_DIR.mkdir(exist_ok=True)

BACKLINK_CACHE_TTL_DAYS = 7

OPR_API = "https://openpagerank.com/api/v1.0/getPageRank"


def _domain_from_url(url: str) -> str:
    return (
        url.replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .split("/")[0]
        .split("?")[0]
    )


def _csv_path(domain: str) -> Path:
    return STORAGE_DIR / f"{domain}.csv"


def _cache_path(domain: str) -> Path:
    return MEMORIES_DIR / f"backlinks_{domain}.json"


def _load_cached(domain: str) -> dict[str, Any] | None:
    path = _cache_path(domain)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        created = datetime.fromisoformat(data.get("checked_at", "2000-01-01"))
        if datetime.now() - created > timedelta(days=BACKLINK_CACHE_TTL_DAYS):
            logger.info("Backlink cache for %s is stale, will refresh", domain)
            return None
        logger.info("Loaded cached backlinks for %s", domain)
        return data
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("Failed to load backlink cache for %s: %s", domain, e)
        return None


def _save_cache(domain: str, data: dict[str, Any]) -> dict[str, Any]:
    data["checked_at"] = datetime.now().isoformat(timespec="seconds")
    path = _cache_path(domain)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved backlinks for %s to %s", domain, path.name)
    return data


def _read_csv_backlinks(domain: str) -> dict[str, Any] | None:
    path = _csv_path(domain)
    if not path.exists():
        return None
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalise headers: lowercase, strip, replace spaces/special chars with _
                norm: dict[str, str] = {}
                for key, val in row.items():
                    if key is None:
                        continue
                    nk = key.strip().lower().replace(" ", "_").replace("-", "_")
                    norm[nk] = (val or "").strip()

                # Map common column name variants
                col_map = {
                    "total_backlinks": ["total_backlinks", "backlinks_total", "backlinks", "total_back_links", "total"],
                    "ref_domains": ["ref_domains", "referring_domains", "referring_domain", "ref_domain", "referral_domains", "referral_domain", "refdomains"],
                    "dofollow": ["dofollow", "do_follow", "followed_links", "follow_links", "dofollow_links", "do_follow_links"],
                    "nofollow": ["nofollow", "no_follow", "nofollow_links", "not_followed", "no_follow_links"],
                    "domain_rating": ["domain_rating", "domain_rating_dr", "dr", "domain_authority", "da", "authority_score", "as", "moz_da", "ahrefs_dr"],
                    "source": ["source", "tool", "export_source", "origin", "provider"],
                }

                def _first_val(variants: list[str]) -> str | None:
                    for v in variants:
                        raw = norm.get(v)
                        if raw:
                            return raw
                    return None

                result: dict[str, Any] = {
                    "domain": domain,
                    "total_backlinks": _first_val(col_map["total_backlinks"]),
                    "ref_domains": _first_val(col_map["ref_domains"]),
                    "dofollow": _first_val(col_map["dofollow"]),
                    "nofollow": _first_val(col_map["nofollow"]),
                    "dr": _first_val(col_map["domain_rating"]),
                    "source": _first_val(col_map["source"]) or "CSV Upload",
                    "status": "AVAILABLE",
                }
                result["checked_at"] = datetime.now().isoformat(timespec="seconds")
                logger.info(
                    "Loaded backlink CSV for %s: %s backlinks, %s ref domains",
                    domain, result["total_backlinks"], result["ref_domains"],
                )
                return result
    except Exception as e:
        logger.warning("Failed to read backlink CSV for %s: %s", domain, e)
    return None


def _try_browseros_scrape(domain: str) -> dict[str, Any] | None:
    try:
        from modules.browseros_client import BrowserOSClient
        client = BrowserOSClient()
        result = client.fetch_backlinks(domain)
        client.close()
        if result.get("status") == "BROWSEROS_NOT_CONNECTED":
            logger.info("BrowserOS not available for backlink scrape")
            return None
        if any(result.get(k) for k in ["total_backlinks", "ref_domains"]):
            result["status"] = "AVAILABLE"
            result["source"] = "browseros_scrape"
            return result
        return None
    except Exception as e:
        logger.warning("BrowserOS backlink scrape failed: %s", e)
        return None


def _fetch_openpagerank(domain: str) -> dict[str, Any] | None:
    """Fetch a free domain authority score (0-10) from OpenPageRank.

    Returns a dict with 'dr' set if successful, or None if unavailable/failed.
    This is a supplementary signal — not a full backlink profile.
    """
    from config.settings import OPENPAGERANK_API_KEY
    key = os.environ.get("OPENPAGERANK_API_KEY", "") or OPENPAGERANK_API_KEY
    if not key:
        return None
    try:
        params = {"domains[]": domain}
        headers = {"API-Key": key, "Accept": "application/json"}
        resp = httpx.get(OPR_API, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.info("OpenPageRank returned HTTP %d for %s", resp.status_code, domain)
            return None
        data = resp.json()
        ranks = data.get("response", [])
        if ranks and isinstance(ranks, list):
            rank = ranks[0].get("page_rank_integer")
            if rank is not None:
                score = int(rank)
                logger.info("OpenPageRank: %s = %d/10", domain, score)
                return {"dr": f"{score}/10", "source": "OpenPageRank"}
    except Exception as e:
        logger.debug("OpenPageRank lookup failed for %s: %s", domain, e)
    return None


def fetch_backlinks(url: str) -> dict[str, Any]:
    domain = _domain_from_url(url)

    csv_data = _read_csv_backlinks(domain)
    if csv_data:
        return _save_cache(domain, csv_data)

    cached = _load_cached(domain)
    if cached:
        return cached

    scraped = _try_browseros_scrape(domain)
    if scraped:
        return _save_cache(domain, scraped)

    opr = _fetch_openpagerank(domain)
    if opr:
        return {
            "domain": domain,
            "status": "OPR_ONLY",
            "dr": opr["dr"],
            "source": opr["source"],
            "total_backlinks": None,
            "ref_domains": None,
            "dofollow": None,
            "nofollow": None,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }

    fallback: dict[str, Any] = {
        "domain": domain,
        "status": "AWAITING_DATA",
        "total_backlinks": "Data Pending",
        "ref_domains": "Data Pending",
        "dofollow": None,
        "nofollow": None,
        "dr": None,
        "source": "Manual Entry Needed",
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }
    logger.info("Backlink data for %s: %s", domain, fallback["status"])
    return fallback
