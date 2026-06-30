from __future__ import annotations

import json
import logging
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, quote

from filelock import FileLock

from api.browser_manager import (
    PLAYWRIGHT_AVAILABLE, STEALTH_AVAILABLE, _STEALTH_HOOK,
    _get_browser_page,
)
from api.crawl_engine import _log_captcha_event
from modules.firecrawl_client import CrawledPage, CrawlResult
from modules.http_pool import sync_client
from modules.url_utils import resolve_and_validate_target
from report.evidence import Evidence
from report.facts import RankingRow

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RANK_CACHE_DIR = OUTPUT_DIR / "rank_cache"
RANK_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "").split(":")[0]


# ── Rank cache (JSON, keyed by domain+keyword, 1h TTL) ──

def _rank_cache_path(domain: str) -> Path:
    safe = domain.lower().replace(".", "_").replace(":", "_")
    return RANK_CACHE_DIR / f"{safe}_ranks.json"


def _load_rank_cache(domain: str) -> dict[str, dict[str, Any]]:
    path = _rank_cache_path(domain)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cutoff = time.time() - 3600
        return {k: v for k, v in data.items() if v.get("ts", 0) > cutoff}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_rank_cache(domain: str, keyword: str, entry: dict[str, Any]) -> None:
    path = _rank_cache_path(domain)
    lock_path = path.with_suffix(".lock")
    lock = FileLock(str(lock_path), timeout=3.0)
    try:
        with lock:
            try:
                data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            except (json.JSONDecodeError, OSError):
                data = {}
            data[keyword] = entry
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── CWV via Playwright Performance API (PSI fallback) ──

def _capture_cwv_via_playwright(target_url: str, strategy: str = "mobile") -> dict[str, Any]:
    if not resolve_and_validate_target(target_url):
        return {"strategy": strategy, "error": "private_target"}
    if not PLAYWRIGHT_AVAILABLE:
        return {"strategy": strategy, "error": "playwright_unavailable"}
    page = _get_browser_page(viewport={"width": 360 if strategy == "mobile" else 1280,
                                        "height": 640 if strategy == "mobile" else 800})
    if page is None:
        return {"strategy": strategy, "error": "no_browser_page"}
    try:
        page.context.add_init_script("""
            window.__cwv = {};
            try {
                new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    if (entries.length > 0) {
                        window.__cwv.lcp_ms = Math.round(entries[entries.length - 1].startTime);
                    }
                }).observe({type: 'largest-contentful-paint', buffered: true});
            } catch(e) { window.__cwv.lcp_error = e.message; }
            try {
                let cls = 0;
                new PerformanceObserver((list) => {
                    list.getEntries().forEach(entry => {
                        if (!entry.hadRecentInput) cls += entry.value;
                    });
                    window.__cwv.cls_score = Math.round(cls * 1000) / 1000;
                }).observe({type: 'layout-shift', buffered: true});
            } catch(e) { window.__cwv.cls_error = e.message; }
        """)
        if strategy == "mobile":
            page.context.add_init_script("""
                Object.defineProperty(navigator, 'maxTouchPoints', { value: 5 });
                Object.defineProperty(navigator, 'hardwareConcurrency', { value: 4 });
                Object.defineProperty(navigator, 'deviceMemory', { value: 4 });
            """)
        page.goto(target_url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2000)

        metrics = page.evaluate("""() => {
            const results = {};
            const perf = performance || {};

            if (window.__cwv) {
                if (window.__cwv.lcp_ms) results.lcp_ms = window.__cwv.lcp_ms;
                if (window.__cwv.cls_score !== undefined) results.cls_score = window.__cwv.cls_score;
            }

            const nav = perf.getEntriesByType('navigation')[0];
            if (nav) {
                results.ttfb_ms = Math.round(nav.responseStart - nav.requestStart);
                results.dom_ready_ms = Math.round(nav.domComplete - nav.domContentLoadedEventEnd);
                results.load_time_ms = Math.round(nav.loadEventEnd - nav.startTime);
            }

            const paints = perf.getEntriesByType('paint') || [];
            paints.forEach(p => {
                if (p.name === 'first-contentful-paint') results.fcp_ms = Math.round(p.startTime);
            });

            const resources = perf.getEntriesByType('resource') || [];
            results.total_resources = resources.length;
            results.total_transfer_size = Math.round(
                resources.reduce((sum, r) => sum + (r.transferSize || 0), 0) / 1024
            );

            return results;
        }""")

        title = page.title() or ""
        logger.info("Playwright CWV %s for %s: LCP=%s FCP=%s CLS=%s TTFB=%s",
                     strategy, target_url,
                     metrics.get("lcp_ms"), metrics.get("fcp_ms"),
                     metrics.get("cls_score"), metrics.get("ttfb_ms"))

        lcp = metrics.get("lcp_ms")
        cls_score = metrics.get("cls_score", 0)
        fcp = metrics.get("fcp_ms")

        score = 90
        if lcp:
            if lcp > 4000: score -= 30
            elif lcp > 2500: score -= 15
            elif lcp > 1500: score -= 5
        if cls_score and cls_score > 0.25:
            score -= 15
        elif cls_score and cls_score > 0.1:
            score -= 5
        if fcp and fcp > 3000:
            score -= 10
        score = max(30, min(100, score))

        return {
            "strategy": strategy,
            "score": score,
            "lcp_seconds": round(metrics["lcp_ms"] / 1000, 2) if metrics.get("lcp_ms") else None,
            "inp_ms": None,
            "cls_score": metrics.get("cls_score"),
            "tbt_ms": None,
            "fcp_seconds": round(metrics["fcp_ms"] / 1000, 2) if metrics.get("fcp_ms") else None,
            "ttfb_seconds": round(metrics["ttfb_ms"] / 1000, 2) if metrics.get("ttfb_ms") else None,
            "opportunities": [],
            "has_field_data": False,
            "error": None,
            "_playwright_raw": metrics,
        }
    except Exception as e:
        logger.warning("Playwright CWV %s failed for %s: %s", strategy, target_url, e)
        return {"strategy": strategy, "error": str(e)}
    finally:
        try:
            page.close()
        except Exception:
            pass


# ── Parallel fetch (PSI, backlinks, GSC, GA4) ──

def _fetch_parallel(url: str) -> dict[str, Any]:
    from modules.pagespeed_client import fetch_pagespeed_metrics
    from modules.backlink_client import fetch_backlinks

    with ThreadPoolExecutor(max_workers=5) as pool:
        psi_m = pool.submit(fetch_pagespeed_metrics, url, "mobile")
        psi_d = pool.submit(fetch_pagespeed_metrics, url, "desktop")
        bl = pool.submit(fetch_backlinks, url)
        gsc = pool.submit(_fetch_gsc_data, url)
        ga4 = pool.submit(_fetch_ga4_data)

    psi_mobile = psi_m.result()
    psi_desktop = psi_d.result()

    if psi_mobile.get("error") and PLAYWRIGHT_AVAILABLE:
        logger.info("PSI mobile unavailable — falling back to Playwright CWV measurement")
        psi_mobile = _capture_cwv_via_playwright(url, "mobile")
    if psi_desktop.get("error") and PLAYWRIGHT_AVAILABLE:
        logger.info("PSI desktop unavailable — falling back to Playwright CWV measurement")
        psi_desktop = _capture_cwv_via_playwright(url, "desktop")

    return {
        "psi_mobile": psi_mobile,
        "psi_desktop": psi_desktop,
        "backlinks": bl.result(),
        "gsc": gsc.result(),
        "ga4": ga4.result(),
    }


# ── Keyword discovery from page content ──

def _discover_keywords_from_page(target_url: str, existing_metrics: dict | None = None) -> list[str]:
    kws: list[str] = []
    if not resolve_and_validate_target(target_url):
        logger.warning("Keyword discovery blocked private target: %s", target_url)
        return kws
    if not kws:
        title = ""
        h1_texts = []
        if existing_metrics and isinstance(existing_metrics, dict):
            title = existing_metrics.get("title", "") or ""
            h1_texts = existing_metrics.get("h1_texts", []) or []
        if not title and not h1_texts:
            import urllib.request
            from bs4 import BeautifulSoup
            try:
                req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read()
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                h1 = soup.find("h1")
                if h1 and h1.get_text(strip=True):
                    h1_texts = [h1.get_text(strip=True)]
            except Exception as e:
                logger.debug("Keyword discovery page fetch failed: %s", e)
        if title:
            words = [w for w in title.split() if len(w) > 2]
            if words:
                kws.append(" ".join(words[:4]))
                if len(words) > 4:
                    kws.append(" ".join(words[:3]))
        if h1_texts:
            for h1_text in h1_texts[:3]:
                words = [w for w in h1_text.split() if len(w) > 2]
                if words:
                    kws.append(" ".join(words[:4]))
    seen: set[str] = set()
    result: list[str] = []
    for kw in kws:
        kw_clean = kw.strip().lower()
        if kw_clean and kw_clean not in seen and len(kw_clean) > 5:
            seen.add(kw_clean)
            result.append(kw)
    return result[:10]


# ── SERP rank tracking ──

def _search_google_via_playwright(keyword: str, target_url: str) -> list[dict[str, Any]]:
    """Scrape Google search results via Playwright. Returns list of
    {position, url, title} for organic results on page 1."""
    if not PLAYWRIGHT_AVAILABLE:
        return []
    if not resolve_and_validate_target(target_url):
        return []

    from modules.url_utils import exact_url_match
    results: list[dict[str, Any]] = []
    page = None
    try:
        page = _get_browser_page(viewport={"width": 1280, "height": 900})
        if page is None:
            return []
        if STEALTH_AVAILABLE and _STEALTH_HOOK is not None:
            _STEALTH_HOOK.apply_stealth_sync(page)

        import random as _rand
        from urllib.parse import quote
        search_url = f"https://www.google.com/search?q={quote(keyword)}&hl=en&num=10"
        page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(_rand.uniform(800, 1500))

        # CAPTCHA check
        for sel in ["form[action*='captcha']", "#captcha", "div.g-recaptcha", "#gs_captcha_ccl"]:
            try:
                if page.locator(sel).is_visible(timeout=600):
                    logger.info("Google CAPTCHA detected for keyword '%s'", keyword)
                    return []
            except Exception:
                pass

        # Parse organic results
        organic = page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('div.g, div[data-sokoban-container]').forEach((el, i) => {
                    const link = el.querySelector('a[href]');
                    const title = el.querySelector('h3');
                    if (link && title) {
                        results.push({
                            position: i + 1,
                            url: link.href,
                            title: title.textContent || ''
                        });
                    }
                });
                return results;
            }
        """) or []

        for r in organic:
            if r.get("url") and r.get("position"):
                results.append({
                    "position": r["position"],
                    "url": r["url"],
                    "title": r.get("title", ""),
                })
    except Exception as e:
        logger.debug("Playwright SERP search failed for '%s': %s", keyword, e)
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass
    return results


def _fetch_rankings_via_serp(
    target_url: str,
    keywords: list[str] | None = None,
    existing_metrics: dict | None = None,
) -> list[RankingRow]:
    from api.rank_providers import any_provider_available

    domain = _domain_from_url(target_url)
    rows: list[RankingRow] = []

    if not keywords:
        keywords = _discover_keywords_from_page(target_url, existing_metrics=existing_metrics)
        if not keywords:
            return rows

    cache = _load_rank_cache(domain)
    uncached: list[str] = []

    for kw in keywords[:10]:
        cached_row = cache.get(kw)
        if cached_row and cached_row.get("position") is not None:
            rows.append(RankingRow(
                keyword=kw,
                position=Evidence.verified(str(cached_row["position"]), "Rank cache"),
                search_volume=0,
                competition="medium",
            ))
        else:
            uncached.append(kw)

    if not uncached:
        logger.info("Rank cache hit for all %d keywords for %s", len(rows), domain)
        return rows

    if any_provider_available():
        # Use API providers (fast, reliable)
        from api.rank_providers import try_providers

        def _check_one(kw: str) -> RankingRow | None:
            try:
                pos, ranking_url, provider = try_providers(
                    keyword=kw, target_url=target_url,
                    location="India", device="desktop",
                )
                if pos is not None:
                    _save_rank_cache(domain, kw, {"position": str(pos), "ts": time.time()})
                    return RankingRow(
                        keyword=kw,
                        position=Evidence.verified(str(pos), provider or "SERP"),
                        search_volume=0,
                        competition="medium",
                    )
                _save_rank_cache(domain, kw, {"position": None, "ts": time.time()})
                return None
            except Exception as e:
                logger.debug("SERP lookup failed for '%s': %s", kw, e)
                return None

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_check_one, kw) for kw in uncached]
            for f in futures:
                result = f.result()
                if result is not None:
                    rows.append(result)
    else:
        # Fallback: scrape Google via Playwright (slower, no API key needed)
        logger.info("No SERP API keys — using Playwright fallback for %d keywords", len(uncached))
        from modules.url_utils import exact_url_match
        for kw in uncached[:5]:  # limit to 5 to avoid CAPTCHA
            try:
                serp_results = _search_google_via_playwright(kw, target_url)
                pos = None
                for r in serp_results:
                    if exact_url_match(target_url, r["url"]):
                        pos = r["position"]
                        break
                _save_rank_cache(domain, kw, {"position": str(pos) if pos else None, "ts": time.time()})
                if pos is not None:
                    rows.append(RankingRow(
                        keyword=kw,
                        position=Evidence.verified(str(pos), "Google (Playwright)"),
                        search_volume=0,
                        competition="medium",
                    ))
                time.sleep(_rand.uniform(2.0, 4.0))  # anti-CAPTCHA delay
            except Exception as e:
                logger.debug("Playwright SERP fallback failed for '%s': %s", kw, e)

    logger.info("SERP rank check: %d/%d keywords for %s", len(rows), len(keywords[:15]), domain)
    return rows


# ── Google Trends ──

def _fetch_google_trends(keyword: str, timeframe: str = "today 12-m") -> dict | None:
    try:
        from config.settings import SERPAPI_KEY
    except Exception:
        SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
    if not SERPAPI_KEY:
        logger.debug("Google Trends skipped: SERPAPI_KEY not set")
        return None

    try:
        params = {
            "engine": "google_trends",
            "q": keyword,
            "date": timeframe,
            "data_type": "TIMESERIES",
            "api_key": SERPAPI_KEY,
            "hl": "en",
            "tz": "420",
        }
        resp = sync_client().get("https://serpapi.com/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.warning("Google Trends error: %s", data["error"])
            return None
        return data.get("interest_over_time")
    except Exception as e:
        logger.debug("Google Trends fetch failed: %s", e)
        return None


# ── GSC data ──

def _fetch_gsc_data(url: str) -> dict | None:
    from config.settings import CREDENTIALS_PATH, GSC_SITE_URL
    site = GSC_SITE_URL or f"sc-domain:{_domain_from_url(url)}"
    creds = CREDENTIALS_PATH or os.environ.get("CREDENTIALS_PATH", "credentials.json")
    if not site or not Path(creds).exists():
        return None
    try:
        from modules.search_console import SearchConsoleClient
        client = SearchConsoleClient(credentials_path=creds, site_url=site)
        end = date.today()
        start = end.replace(day=1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        current = client.query(start_date=start.isoformat(), end_date=end.isoformat(), row_limit=10)
        previous = client.query(start_date=prev_start.isoformat(), end_date=prev_end.isoformat(), row_limit=10)
        if current.get("status") != "ok":
            return None
        clicks = current.get("total_clicks", 0)
        impressions = current.get("total_impressions", 0)
        prev_clicks = previous.get("total_clicks", 0) or 1
        prev_impressions = previous.get("total_impressions", 0) or 1
        clicks_change = round(((clicks - prev_clicks) / prev_clicks) * 100)
        impressions_change = round(((impressions - prev_impressions) / prev_impressions) * 100)
        logger.info("GSC: %s clicks, %s impressions (%s%%, %s%%)", clicks, impressions, clicks_change, impressions_change)
        return {
            "clicks": clicks, "impressions": impressions,
            "clicks_change": clicks_change, "impressions_change": impressions_change,
        }
    except Exception as e:
        logger.debug("GSC fetch failed: %s", e)
        return None


# ── GA4 data ──

def _fetch_ga4_data() -> dict | None:
    from config.settings import CREDENTIALS_PATH, GA4_PROPERTY_ID
    creds = CREDENTIALS_PATH or os.environ.get("CREDENTIALS_PATH", "credentials.json")
    if not GA4_PROPERTY_ID or not Path(creds).exists():
        return None
    try:
        from modules.ga4_client import AnalyticsClient
        client = AnalyticsClient(credentials_path=creds, property_id=GA4_PROPERTY_ID)
        data = client.get_metrics()
        if data.get("organic_users") == "Access Required":
            logger.info("GA4: Access Required — service account not granted access")
            return None
        logger.info("GA4: %s organic users, %s sessions", data.get("organic_users"), data.get("sessions"))
        return data
    except Exception as e:
        logger.debug("GA4 fetch failed: %s", e)
        return None


# ── SERP screenshot ──

def _capture_serp_preview(target_url: str) -> bytes | None:
    if not resolve_and_validate_target(target_url):
        logger.warning("SERP preview blocked private target: %s", target_url)
        return None
    if not PLAYWRIGHT_AVAILABLE:
        return None
    domain = _domain_from_url(target_url)

    vp_width = 1280 + random.randint(-4, 4)
    vp_height = 900 + random.randint(-4, 4)
    page = _get_browser_page(viewport={"width": vp_width, "height": vp_height})
    if page is None:
        return None
    try:
        if STEALTH_AVAILABLE and _STEALTH_HOOK is not None:
            _STEALTH_HOOK.apply_stealth_sync(page)

        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/125.0.0.0 Safari/537.36")
        page.set_extra_http_headers({"User-Agent": ua,
                                      "Accept-Language": "en-US,en;q=0.9",
                                      "Accept": "text/html,application/xhtml+xml"})

        search_url = f"https://www.google.com/search?q=site:{quote(domain)}&hl=en"
        page.goto(search_url, wait_until="commit", timeout=20000)
        page.wait_for_timeout(random.uniform(500, 1200))

        captcha_selectors = [
            "form[action*='captcha']", "#captcha", "iframe[src*='recaptcha']",
            "div.g-recaptcha", "input[name*='captcha']",
            "#gs_captcha_ccl", "iframe[src*='checkpoint']",
        ]
        is_captcha = False
        for sel in captcha_selectors:
            try:
                if page.locator(sel).is_visible(timeout=800):
                    is_captcha = True
                    break
            except Exception:
                pass
        if is_captcha:
            _log_captcha_event("captcha_detected", domain, search_url)
            logger.info("SERP preview skipped: Google CAPTCHA detected for %s", domain)
            return None

        page.wait_for_timeout(random.uniform(600, 1400))

        target_x = random.randint(200, 800)
        target_y = random.randint(100, 500)
        page.mouse.move(target_x, target_y, steps=random.randint(5, 12))

        scroll_amount = random.randint(80, 250)
        page.mouse.wheel(0, scroll_amount)
        page.wait_for_timeout(random.uniform(300, 700))

        try:
            accept = page.locator("button:has-text('Accept all'), button:has-text('I agree')")
            if accept.is_visible(timeout=1500):
                accept.click()
                page.wait_for_timeout(random.uniform(500, 1000))
        except Exception:
            pass

        for sel in captcha_selectors:
            try:
                if page.locator(sel).is_visible(timeout=500):
                    _log_captcha_event("captcha_post_interaction", domain, search_url)
                    return None
            except Exception:
                pass

        page.wait_for_timeout(random.uniform(400, 800))
        result_area = page.locator("#search")
        if result_area.is_visible(timeout=2000):
            png = result_area.screenshot(type="png")
        else:
            png = page.screenshot(full_page=False, type="png")
        _log_captcha_event("success", domain, search_url)
        logger.info("SERP preview captured for %s (%d bytes)", domain, len(png))
        return png
    except Exception as e:
        _log_captcha_event("error", domain, str(e))
        logger.info("SERP preview skipped for %s: %s", domain, e)
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass
