from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from filelock import FileLock

from api.browser_manager import (
    PLAYWRIGHT_AVAILABLE, STEALTH_AVAILABLE, _STEALTH_HOOK,
    _get_browser_page,
)
from modules.firecrawl_client import FirecrawlClient, CrawledPage, CrawlResult
from modules.http_pool import sync_client
from modules.url_utils import resolve_and_validate_target

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

BROWSERLESS_API_KEY = os.environ.get("BROWSERLESS_API_KEY", "")

LOCAL_ANALYZER_AVAILABLE = False
try:
    from pyseoanalyzer import analyze as _pyseo_analyze
    LOCAL_ANALYZER_AVAILABLE = True
    logger.info("pyseoanalyzer available")
except ImportError:
    pass


# ── Content security blocklist ──
_MALWARE_DOMAINS: set[str] = {
    "malware.testing.google.test",
    "malwaredomainlist.com",
    "zeustracker.abuse.ch",
    "ransomwaretracker.abuse.ch",
    "feodotracker.abuse.ch",
    "sslbl.abuse.ch",
    "urlhaus.abuse.ch",
    "threatfox.abuse.ch",
}

_BLOCKED_MIME_PATTERNS: list[str] = [
    ".exe", ".scr", ".vbs", ".bat", ".cmd", ".ps1",
    ".jar", ".class", ".swf",
    ".msi", ".msp", ".mst",
    ".dll", ".ocx", ".cpl", ".sys",
    ".zip", ".rar", ".7z", ".tar.gz",
]


def _domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "").split(":")[0]


def _is_malware_request(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower()
        for blocked in _MALWARE_DOMAINS:
            if hostname == blocked or hostname.endswith("." + blocked):
                return True
        return False
    except Exception:
        return False


def _is_blocked_mime(url: str) -> bool:
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
    except Exception:
        path = url.lower()
    for pat in _BLOCKED_MIME_PATTERNS:
        if path.endswith(pat):
            return True
    return False





def _make_security_route_handler(page: Any) -> callable:
    def _route_handler(route):
        req = route.request
        req_url = req.url

        if _is_malware_request(req_url):
            logger.debug("BLOCKED (malware domain): %s", req_url[:120])
            return route.abort("blockedbyclient")

        if _is_blocked_mime(req_url):
            logger.debug("BLOCKED (dangerous extension): %s", req_url[:120])
            return route.abort("blockedbyclient")

        return route.continue_()

    return _route_handler


# ── HTML parsing ──

def _parse_rendered_html(html: str, target_url: str) -> dict[str, Any]:
    from bs4 import BeautifulSoup
    result = {
        "h1_count": 0, "h1_texts": [],
        "meta_description": "", "title": "",
        "alt_missing": 0, "alt_total": 0,
        "total_images_found": 0,
        "missing_title_tags": 0,
        "word_count": 0, "has_yoast_schema": False,
        "has_og_tags": False,
    }
    try:
        soup = BeautifulSoup(html, "html.parser")
        h1s = soup.find_all("h1")
        result["h1_count"] = len(h1s)
        result["h1_texts"] = [h.get_text(strip=True) for h in h1s if h.get_text(strip=True)]
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["meta_description"] = meta_desc["content"].strip()
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            result["title"] = title_tag.get_text(strip=True)
        og_tags = soup.find_all("meta", attrs={"property": True})
        result["has_og_tags"] = any(t.get("property", "").startswith("og:") for t in og_tags)
        all_imgs = soup.find_all("img")
        result["total_images_found"] = len(all_imgs)
        result["alt_total"] = len(all_imgs)
        missing_alts = 0
        missing_titles = 0
        for img in all_imgs:
            if not img.get("alt") or img["alt"].strip() == "":
                missing_alts += 1
            if not img.get("title") or img["title"].strip() == "":
                missing_titles += 1
        result["alt_missing"] = missing_alts
        result["missing_title_tags"] = missing_titles
        body = soup.find("body")
        if body:
            result["word_count"] = len(body.get_text(strip=True).split())
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string and ("@type" in script.string):
                result["has_yoast_schema"] = True
                break
    except Exception as e:
        logger.warning("HTML parse failed: %s", e)
    return result


# ── Tier 2a: Playwright headless ──

def _run_playwright_headless(target_url: str) -> dict[str, Any]:
    logger.info("Playwright: rendering %s", target_url)
    raw = {}
    page = _get_browser_page()
    if page is None:
        logger.warning("Playwright headless: no browser page available")
        return raw
    try:
        if STEALTH_AVAILABLE and _STEALTH_HOOK is not None:
            _STEALTH_HOOK.apply_stealth_sync(page)

        security_handler = _make_security_route_handler(page)
        page.route("**/*", security_handler)

        broken_responses: list[dict[str, Any]] = []
        redirect_chains: list[dict[str, Any]] = []

        def _on_response(resp):
            status = resp.status
            req_url = resp.url
            if status >= 400:
                broken_responses.append({"url": req_url, "status": status, "reason": resp.status_text})
            elif status in (301, 302, 303, 307, 308):
                redirect_chains.append({"url": req_url, "status": status})

        page.on("response", _on_response)
        page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight); window.scrollTo(0, 0);")

        # Comprehensive SEO extraction in a single JS pass
        seo = page.evaluate("""() => {
            const results = {
                title: document.title || '',
                meta_description: '',
                h1_texts: [],
                h1_count: 0,
                total_images_found: 0,
                alt_missing: 0,
                alt_total: 0,
                has_og_tags: false,
                has_yoast_schema: false,
                word_count: 0,
                links: [],
            };
            // Meta description
            const meta = document.querySelector('meta[name="description"]');
            if (meta) results.meta_description = meta.content || '';
            // H1s
            const h1s = document.querySelectorAll('h1');
            results.h1_count = h1s.length;
            h1s.forEach(h => { if (h.textContent.trim()) results.h1_texts.push(h.textContent.trim()); });
            // Images
            document.querySelectorAll('img').forEach(img => {
                results.total_images_found++;
                const alt = (img.alt || '').trim();
                const title = (img.title || '').trim();
                if (!alt) results.alt_missing++;
                if (!title) results.alt_missing++;
                results.alt_total++;
            });
            // OG tags
            document.querySelectorAll('meta[property]').forEach(m => {
                if (m.getAttribute('property').startsWith('og:')) results.has_og_tags = true;
            });
            // Schema
            document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                if (s.textContent && s.textContent.includes('@type')) results.has_yoast_schema = true;
            });
            // Word count
            const body = document.body;
            if (body) results.word_count = (body.textContent || '').trim().split(/\\s+/).filter(Boolean).length;
            // Links
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.href;
                if (href && href.startsWith('http')) results.links.push(href);
            });
            return results;
        }""") or {}

        raw = {
            "title": seo.get("title", ""),
            "meta_description": seo.get("meta_description", ""),
            "h1_count": seo.get("h1_count", 0),
            "h1_texts": seo.get("h1_texts", []),
            "total_images_found": seo.get("total_images_found", 0),
            "alt_missing": seo.get("alt_missing", 0),
            "alt_total": seo.get("alt_total", 0),
            "has_og_tags": seo.get("has_og_tags", False),
            "has_yoast_schema": seo.get("has_yoast_schema", False),
            "word_count": seo.get("word_count", 0),
            "link_health": {
                "broken_in_page_load": broken_responses,
                "redirects_in_page_load": redirect_chains,
                "all_hrefs": seo.get("links", []),
            },
            "_pages": [],
        }
        logger.info("Playwright OK: %d images, %d links (%d broken in load), %d h1",
                     raw["total_images_found"], len(seo.get("links", [])),
                     len(broken_responses), raw["h1_count"])
    except Exception as e:
        logger.warning("Playwright headless failed: %s", e)
    finally:
        try:
            page.close()
        except Exception:
            pass
    return raw


def _capture_page_preview(target_url: str) -> bytes | None:
    if not resolve_and_validate_target(target_url):
        logger.warning("Page preview blocked private target: %s", target_url)
        return None
    if not PLAYWRIGHT_AVAILABLE:
        return None
    page = _get_browser_page(viewport={"width": 1280, "height": 900})
    if page is None:
        return None
    try:
        if STEALTH_AVAILABLE and _STEALTH_HOOK is not None:
            _STEALTH_HOOK.apply_stealth_sync(page)
        page.goto(target_url, wait_until="networkidle", timeout=20000)
        png = page.screenshot(full_page=False, type="png")
        logger.info("Page preview captured (%d bytes)", len(png))
        return png
    except Exception as e:
        logger.debug("Page preview capture failed: %s", e)
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass


# ── CAPTCHA telemetry ──

_CAPTCHA_LOG: list[dict[str, Any]] = []


def _log_captcha_event(outcome: str, domain: str, detail: str = "") -> None:
    event = {
        "ts": time.time(),
        "outcome": outcome,
        "domain": domain,
        "detail": detail[:120],
    }
    _CAPTCHA_LOG.append(event)
    logger.debug("CAPTCHA telemetry: %s for %s", outcome, domain)
    try:
        log_path = OUTPUT_DIR / "captcha_telemetry.json"
        lock_path = OUTPUT_DIR / "captcha_telemetry.json.lock"
        lock = FileLock(str(lock_path), timeout=3.0)
        with lock:
            existing: list[dict[str, Any]] = []
            if log_path.exists():
                raw = log_path.read_text(encoding="utf-8")
                if raw.strip():
                    existing = json.loads(raw)
            existing.append(event)
            log_path.write_text(
                json.dumps(existing[-500:], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
    except Exception:
        pass


def captcha_summary() -> dict[str, Any]:
    if not _CAPTCHA_LOG:
        return {"total": 0, "summary": "No CAPTCHA events recorded this session."}
    total = len(_CAPTCHA_LOG)
    successes = sum(1 for e in _CAPTCHA_LOG if e["outcome"] == "success")
    blocks = sum(
        1 for e in _CAPTCHA_LOG
        if e["outcome"] in ("captcha_detected", "captcha_post_interaction")
    )
    errors = sum(1 for e in _CAPTCHA_LOG if e["outcome"] == "error")
    rate = round(successes / total * 100, 1) if total else 0
    return {
        "total": total,
        "successes": successes,
        "blocks": blocks,
        "errors": errors,
        "success_rate_pct": rate,
        "summary": f"{successes}/{total} SERP previews captured ({rate}% success, {blocks} blocked, {errors} errors).",
    }


# ── Tier 2b: Cloud stealth browser ──

def _run_cloud_stealth_browser(target_url: str) -> dict[str, Any]:
    if not BROWSERLESS_API_KEY:
        return {}
    if not resolve_and_validate_target(target_url):
        logger.warning("Cloud stealth blocked private target: %s", target_url)
        return {}
    logger.info("Cloud stealth: connecting to browserless.io for %s", target_url)
    raw = {}
    try:
        wss_url = f"wss://chrome.browserless.io?token={BROWSERLESS_API_KEY}"
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_to_browser(wss_url)
            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()
                if STEALTH_AVAILABLE:
                    _STEALTH_HOOK.apply_stealth_sync(page)
                page.goto(target_url, wait_until="networkidle", timeout=45000)
                raw = _parse_rendered_html(page.content(), target_url)
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
        finally:
            pw.stop()
        logger.info("Cloud stealth OK: %d images (%d missing alt)",
                     raw.get("total_images_found", 0), raw.get("alt_missing", 0))
    except Exception as e:
        logger.warning("Cloud stealth browser failed: %s", e)
    return raw


# ── Tier 4: urllib/BeautifulSoup ──

def _extract_seo_via_urllib(target_url: str) -> dict[str, Any]:
    if not resolve_and_validate_target(target_url):
        logger.warning("urllib blocked private target: %s", target_url)
        return {}
    import urllib.request
    from bs4 import BeautifulSoup
    result = {
        "h1_count": 0, "h1_texts": [],
        "meta_description": "", "title": "",
        "alt_missing": 0, "alt_total": 0,
        "word_count": 0, "has_yoast_schema": False,
        "link_health": {"all_hrefs": []},
    }
    try:
        req = urllib.request.Request(
            target_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read()
        soup = BeautifulSoup(html, "html.parser")
        result = _parse_rendered_html(html, target_url)
        all_hrefs = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href.startswith("http"):
                all_hrefs.append(href)
            elif href.startswith("/") or href.startswith("#") or (not href.startswith("javascript:")):
                full = urljoin(target_url, href)
                if full.startswith("http"):
                    all_hrefs.append(full)
        result["link_health"] = {"all_hrefs": list(set(all_hrefs))}
        logger.info("urllib parse OK for %s: title=%s, h1=%d, images=%d, links=%d",
                     target_url, result["title"], result["h1_count"], result["alt_total"], len(all_hrefs))
    except Exception as e:
        logger.warning("urllib parse failed for %s: %s", target_url, e)
    return result


# ── Link health check ──

def _discover_internal_links(target_url: str) -> list[str]:
    """Extract all internal links from a page via Playwright."""
    if not PLAYWRIGHT_AVAILABLE:
        return []
    page = _get_browser_page()
    if page is None:
        return []
    links: list[str] = []
    try:
        if STEALTH_AVAILABLE and _STEALTH_HOOK is not None:
            _STEALTH_HOOK.apply_stealth_sync(page)
        page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1000)
        links = page.evaluate("""() => {
            const links = [];
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.href;
                if (href && href.startsWith('http')) links.push(href);
            });
            return [...new Set(links)];
        }""") or []
        logger.info("Discovered %d links on %s", len(links), target_url)
    except Exception as e:
        logger.debug("Link discovery failed for %s: %s", target_url, e)
    finally:
        try:
            page.close()
        except Exception:
            pass
    return links


def _check_link_health(links: list[str], base_url: str) -> dict[str, Any]:
    domain = _domain_from_url(base_url)
    internal_links: list[str] = []

    for l in links[:30]:
        if not l.startswith("http"):
            continue
        parsed = urlparse(l)
        netloc = parsed.netloc.lower().replace("www.", "").split(":")[0]
        if netloc == domain or not parsed.netloc:
            internal_links.append(l)

    broken: list[str] = []
    redirects: list[str] = []

    def _check_one(link: str) -> tuple[str, str | None]:
        if not resolve_and_validate_target(link):
            return (link, "broken")
        try:
            client = sync_client()
            r = client.head(link, follow_redirects=False, timeout=3.0)
            if r.status_code == 405:
                r2 = client.get(link, timeout=3.0)
                return (link, "broken" if r2.status_code >= 400 else None)
            if r.status_code >= 400:
                return (link, "broken")
            if r.status_code in (301, 302, 303, 307, 308):
                return (link, "redirect")
            return (link, None)
        except Exception:
            return (link, "broken")

    if internal_links:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_check_one, link) for link in internal_links]
            for f in as_completed(futures):
                link, result = f.result()
                if result == "broken":
                    broken.append(link)
                elif result == "redirect":
                    redirects.append(link)

    return {
        "total_links_checked": len(internal_links),
        "internal_links": len(internal_links),
        "external_links": 0,
        "broken_links": broken,
        "redirect_links": redirects,
        "healthy_count": len(internal_links) - len(broken),
    }


# ── Tiered crawl orchestrator ──

def run_local_opensource_seo_audit(target_url: str, crawl_mode: str = "single") -> dict[str, Any]:
    raw: dict[str, Any] = {}

    if not resolve_and_validate_target(target_url):
        logger.warning("Blocked crawl to private/internal address: %s", target_url)
        return raw

    if PLAYWRIGHT_AVAILABLE:
        logger.info("Crawl tier: 1 — Playwright headless for %s", target_url)
        raw = _run_playwright_headless(target_url)

    if not raw and BROWSERLESS_API_KEY:
        logger.info("Crawl tier: 2 — Cloud stealth browser for %s", target_url)
        raw = _run_cloud_stealth_browser(target_url)

    if (crawl_mode == "full" or not raw) and LOCAL_ANALYZER_AVAILABLE:
        logger.info("Crawl tier: 3 — pyseoanalyzer for %s (mode=%s)", target_url, crawl_mode)
        try:
            output = _pyseo_analyze(target_url, follow_links=(crawl_mode == "full"))
            if isinstance(output, dict):
                psa_pages = output.get("pages", [])
                if crawl_mode == "full" and psa_pages:
                    all_pages: list[dict[str, Any]] = list(raw.get("pages", []))
                    all_pages.extend(psa_pages)
                    raw["pages"] = all_pages
                    if output.get("keywords"):
                        raw["keywords"] = output["keywords"]
                if not raw:
                    raw = output
        except Exception as e:
            logger.warning("pyseoanalyzer failed: %s", e)

    # Playwright multi-page crawl when full mode requested and no multi-page data yet
    if crawl_mode == "full" and PLAYWRIGHT_AVAILABLE:
        existing_pages = raw.get("pages", [])
        if len(existing_pages) <= 1:
            logger.info("Playwright full crawl: discovering internal links for %s", target_url)
            internal_links = _discover_internal_links(target_url)
            # Filter to same domain, skip already-crawled
            from urllib.parse import urlparse
            base_domain = urlparse(target_url).netloc.lower().replace("www.", "")
            to_crawl = []
            seen_urls = {target_url.rstrip("/")}
            for link in internal_links:
                link_domain = urlparse(link).netloc.lower().replace("www.", "")
                if link_domain == base_domain and link.rstrip("/") not in seen_urls:
                    to_crawl.append(link)
                    seen_urls.add(link.rstrip("/"))
            to_crawl = to_crawl[:14]  # Max 15 total pages (1 already crawled)
            if to_crawl:
                logger.info("Playwright full crawl: %d additional pages to crawl", len(to_crawl))
                pages_list = list(existing_pages) if existing_pages else []
                for crawl_url in to_crawl:
                    try:
                        page_data = _run_playwright_headless(crawl_url)
                        if page_data:
                            pages_list.append({
                                "url": crawl_url,
                                "title": page_data.get("title", ""),
                                "description": page_data.get("meta_description", ""),
                                "text": "",
                                "warnings": [],
                            })
                    except Exception as e:
                        logger.debug("Playwright crawl of %s failed: %s", crawl_url, e)
                raw["pages"] = pages_list
                logger.info("Playwright full crawl complete: %d pages total", len(pages_list))

    if not raw:
        logger.info("Crawl tier: 4 — urllib/BeautifulSoup for %s", target_url)
        raw = _extract_seo_via_urllib(target_url)

    if raw:
        logger.info("Crawl success — tier produced %d fields: title=%s, h1=%d, images=%d, pages=%d",
                     len(raw), raw.get("title", "")[:40],
                     raw.get("h1_count", 0), raw.get("total_images_found", 0),
                     len(raw.get("pages", [])))
    else:
        logger.warning("All crawl tiers failed for %s", target_url)

    tech = raw.get("technical", {}) if isinstance(raw.get("technical"), dict) else {}
    content = raw.get("content", {}) if isinstance(raw.get("content"), dict) else {}
    pages = raw.get("pages", []) if isinstance(raw.get("pages"), list) else []

    img_count = raw.get("total_images_found", raw.get("alt_total", 0))
    missing_alt = raw.get("alt_missing", 0)
    health = raw.get("score") or 98
    if img_count > 0 and missing_alt > 0:
        penalty = int((missing_alt / img_count) * 30)
        health = max(40, 100 - penalty)

    if len(pages) > 1:
        missing_h1_total = 0
        pages_missing_meta = 0
        for p in pages:
            has_title = bool(p.get("title"))
            has_desc = bool(p.get("description"))
            if not has_title or not has_desc:
                pages_missing_meta += 1
            for w in p.get("warnings", []):
                wl = str(w).lower()
                if "h1" in wl or "heading" in wl:
                    missing_h1_total += 1
        pages_audited = len(pages)
    else:
        missing_h1_total = 0
        pages_missing_meta = 0
        pages_audited = 1

    return {
        "url": target_url,
        "health_score": health,
        "pages_audited": max(1, pages_audited),
        "missing_h1_count": (tech.get("missing_h1") or missing_h1_total or
                              (1 if raw.get("h1_count", 1) == 0 else 0)),
        "missing_meta_tags": (tech.get("missing_meta_description") or pages_missing_meta or 0),
        "missing_alt_tags": missing_alt or content.get("missing_image_alt") or 0,
        "total_images_found": img_count,
        "thin_pages_detected": content.get("thin_content_pages") or 0,
        "has_yoast_schema": bool(raw.get("yoast_detected")) or raw.get("has_yoast_schema", False),
        "title": raw.get("title", ""),
        "meta_description": raw.get("meta_description", ""),
        "h1_texts": tech.get("h1_texts", []) or raw.get("h1_texts", []),
        "word_count": content.get("total_words") or raw.get("word_count", 0),
        "link_health": raw.get("link_health", {}),
        "_pages": [dict(p) for p in pages],
    }


def build_defensive_audit_payload(target_url: str, raw_analyzer_dict: dict[str, Any] | None = None) -> dict[str, Any]:
    if raw_analyzer_dict is None:
        raw_analyzer_dict = {}
    return {
        "url": target_url,
        "health_score": raw_analyzer_dict.get("health_score"),
        "pages_audited": raw_analyzer_dict.get("pages_audited"),
        "missing_h1_count": raw_analyzer_dict.get("missing_h1_count") or 0,
        "missing_meta_tags": raw_analyzer_dict.get("missing_meta_tags") or 0,
        "missing_alt_tags": raw_analyzer_dict.get("missing_alt_tags") or 0,
        "total_images_found": raw_analyzer_dict.get("total_images_found") or 0,
        "thin_pages_detected": raw_analyzer_dict.get("thin_pages_detected") or 0,
        "has_yoast_schema": bool(raw_analyzer_dict.get("has_yoast_schema")),
        "title": raw_analyzer_dict.get("title", ""),
        "meta_description": raw_analyzer_dict.get("meta_description", ""),
    }
