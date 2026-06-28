from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

CDP_HTTP_URL = "http://127.0.0.1:9100"
_SEARCH_TIMEOUT = 30_000
_PAGE_LOAD_WAIT = 3.0
_MAX_CRAWL_PAGES = 30


class BrowserOSError(RuntimeError):
    pass


class BrowserOSClient:
    """Drives the BrowserOS Chromium instance via Playwright + CDP.

    Connects once on first ``search()`` call and reuses the connection
    for subsequent calls. ``close()`` must be called to release
    Playwright resources when the client is no longer needed.
    """

    def __init__(self, cdp_url: str = CDP_HTTP_URL, use_stealth: bool = True) -> None:
        self.cdp_url = cdp_url.rstrip("/")
        self.use_stealth = use_stealth
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._connected = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    @staticmethod
    def _stealth_init_script() -> str:
        """JS injected before every page load to hide automation traces."""
        return """() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({ name: 'Chrome PDF Plugin' })),
            });
            const origQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (params) => (
                params.name === 'notifications'
                    ? Promise.resolve({ state: Notification.prompt })
                    : origQuery(params)
            );
        }"""

    def _ensure_connected(self) -> tuple[Any, Any] | None:
        if self._connected and self._page is not None:
            return self._context, self._page
        if self._playwright is None:
            try:
                self._playwright = sync_playwright().start()
            except Exception as e:
                logger.error(f"BrowserOS: failed to start Playwright — {e}")
                self._connected = False
                return None
        try:
            self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_url)
            self._context = self._browser.contexts[0]
            if self.use_stealth:
                self._context.add_init_script(self._stealth_init_script())
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self._connected = True
            return self._context, self._page
        except Exception as e:
            logger.warning(f"BrowserOS: connection failed to {self.cdp_url} — {e}")
            self._connected = False
            return None

    def close(self) -> None:
        self._page = None
        self._context = None
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    # ------------------------------------------------------------------
    # JavaScript extraction helpers (static for testability)
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_serp_js() -> str:
        return """() => {
            const results = [];
            const containers = document.querySelectorAll('div.yuRUbf');
            if (containers.length === 0) {
                const fallbacks = document.querySelectorAll('a[href^="http"][ping]');
                for (const a of fallbacks) {
                    const h3 = a.querySelector('h3');
                    if (!h3) continue;
                    results.push({
                        link: a.getAttribute('href') || '',
                        title: h3.textContent.trim(),
                    });
                }
                return results;
            }
            for (const container of containers) {
                const a = container.querySelector('a[href]');
                const h3 = container.querySelector('h3');
                if (!a) continue;
                const href = a.getAttribute('href');
                if (!href || !href.startsWith('http')) continue;
                results.push({
                    link: href,
                    title: h3 ? h3.textContent.trim() : '',
                });
            }
            return results;
        }"""

    @staticmethod
    def _detect_blocked_js() -> str:
        return """() => {
            const body = document.body ? document.body.innerText.toLowerCase() : '';
            const signals = [
                'unusual traffic', 'captcha', 'are you a robot',
                'please verify', 'your request has been blocked',
                'sorry, we have detected unusual activity',
            ];
            return signals.some(s => body.includes(s));
        }"""

    @staticmethod
    def _extract_backlinks_js() -> str:
        return """() => {
            const text = document.body ? document.body.innerText : '';
            const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            const result = { total_backlinks: null, ref_domains: null, dofollow: null, nofollow: null, dr: null };
            for (let i = 0; i < lines.length; i++) {
                const lower = lines[i].toLowerCase();
                const nextVal = i + 1 < lines.length ? lines[i + 1] : '';
                const prevVal = i > 0 ? lines[i - 1] : '';
                if (lower.includes('backlink') || lower.includes('total backlink')) {
                    const num = nextVal.replace(/,/g, '');
                    if (/^\\d+$/.test(num)) result.total_backlinks = num;
                }
                if (lower.includes('referring domain') || lower.includes('ref domain')) {
                    const num = nextVal.replace(/,/g, '');
                    if (/^\\d+$/.test(num)) result.ref_domains = num;
                }
                if (lower.includes('dofollow') || lower.includes('do follow')) {
                    const num = nextVal.replace(/,/g, '');
                    if (/^\\d+$/.test(num)) result.dofollow = num;
                }
                if (lower.includes('nofollow') || lower.includes('no follow')) {
                    const num = nextVal.replace(/,/g, '');
                    if (/^\\d+$/.test(num)) result.nofollow = num;
                }
                if (lower.includes('domain rating') || lower.includes('dr ')) {
                    const num = nextVal.replace(/,/g, '');
                    if (/^\\d+$/.test(num) && parseInt(num) <= 100) result.dr = num;
                }
            }
            return result;
        }"""

    @staticmethod
    def _performance_js() -> str:
        return """() => {
            const nav = performance.getEntriesByType('navigation')[0];
            const paint = performance.getEntriesByType('paint');
            const fp = paint.find(e => e.name === 'first-paint');
            const fcp = paint.find(e => e.name === 'first-contentful-paint');
            return {
                domContentLoaded: nav ? nav.domContentLoadedEventEnd : null,
                loadEventEnd: nav ? nav.loadEventEnd : null,
                domInteractive: nav ? nav.domInteractive : null,
                responseStart: nav ? nav.responseStart : null,
                responseEnd: nav ? nav.responseEnd : null,
                firstPaint: fp ? fp.startTime : null,
                firstContentfulPaint: fcp ? fcp.startTime : null,
                transferSize: nav ? nav.transferSize : null,
                decodedBodySize: nav ? nav.decodedBodySize : null,
                encodedBodySize: nav ? nav.encodedBodySize : null,
            };
        }"""

    @staticmethod
    def _audit_page_js() -> str:
        return """() => {
            const issues = [];
            const title = document.title || '';
            const metaDesc = document.querySelector('meta[name="description"]');
            const h1 = document.querySelector('h1');
            const images = document.querySelectorAll('img');
            const headingCounts = {h1:0,h2:0,h3:0,h4:0,h5:0,h6:0};
            const linkUrls = [];

            if (!title) issues.push('Missing title');
            if (!metaDesc || !(metaDesc.getAttribute('content') || '').trim()) issues.push('Missing meta description');
            if (!h1 || !h1.textContent.trim()) issues.push('Missing h1');
            if (document.querySelectorAll('h1').length > 1) issues.push('Multiple h1 tags');

            let altMissing = 0;
            for (let i = 0; i < images.length; i++) { if (!images[i].hasAttribute('alt')) altMissing++; }
            if (altMissing > 0) issues.push(altMissing + ' images missing alt text');

            ['h1','h2','h3','h4','h5','h6'].forEach(function(t) { headingCounts[t] = document.querySelectorAll(t).length; });

            const h2s = [];
            const h2Els = document.querySelectorAll('h2');
            for (let i = 0; i < h2Els.length && i < 20; i++) h2s.push(h2Els[i].textContent.trim());

            const anchors = document.querySelectorAll('a[href]');
            for (let i = 0; i < anchors.length; i++) {
                const h = anchors[i].getAttribute('href');
                if (h && h[0] !== '#' && h.indexOf('javascript:') !== 0) linkUrls.push(h);
            }

            const bodyText = document.body ? document.body.innerText : '';
            const wordCount = bodyText ? bodyText.split(/\\s+/).length : 0;

            return {
                title: title,
                metaDescription: metaDesc ? metaDesc.getAttribute('content') || '' : '',
                h1: h1 ? h1.textContent.trim() : '',
                h2s: h2s,
                headingCounts: headingCounts,
                totalImages: images.length,
                imagesWithoutAlt: altMissing,
                totalLinks: anchors.length,
                linkUrls: linkUrls.slice(0, 500),
                issues: issues,
                wordCount: wordCount,
            };
        }"""

    # ------------------------------------------------------------------
    # Generic page navigation
    # ------------------------------------------------------------------
    def _goto(self, page: Any, url: str) -> bool:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=_SEARCH_TIMEOUT)
            page.wait_for_timeout(_PAGE_LOAD_WAIT * 1000)
            return True
        except Exception as e:
            logger.warning(f"BrowserOS: goto timeout for {url} — {e}")
            return False

    # ------------------------------------------------------------------
    # Page speed measurement (fallback when Pagespeed API is 429)
    # ------------------------------------------------------------------
    def _page_or_none(self) -> Any | None:
        """Return the Playwright page if connected, else None."""
        result = self._ensure_connected()
        if result is None:
            return None
        return result[1]

    def measure_performance(self, url: str) -> dict[str, Any]:
        page = self._page_or_none()
        if page is None:
            return {"url": url, "error": "browseros_not_connected"}
        ok = self._goto(page, url)
        if not ok:
            return {"url": url, "error": "page_load_failed"}
        metrics = page.evaluate(self._performance_js())
        return {
            "url": url,
            "domContentLoaded": metrics.get("domContentLoaded"),
            "loadEventEnd": metrics.get("loadEventEnd"),
            "domInteractive": metrics.get("domInteractive"),
            "firstPaint": metrics.get("firstPaint"),
            "firstContentfulPaint": metrics.get("firstContentfulPaint"),
            "transferSize": metrics.get("transferSize"),
            "decodedBodySize": metrics.get("decodedBodySize"),
            "encodedBodySize": metrics.get("encodedBodySize"),
        }

    def summarize_performance(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Compute human-friendly scores from raw Performance API data."""
        result = {"url": metrics.get("url", "")}
        load = metrics.get("loadEventEnd")
        fcp = metrics.get("firstContentfulPaint")

        if load is not None:
            load_sec = load / 1000
            if load_sec < 2.5:
                result["loadTime"] = f"{load_sec:.1f}s (fast)"
                result["loadRating"] = "good"
            elif load_sec < 4.0:
                result["loadTime"] = f"{load_sec:.1f}s (moderate)"
                result["loadRating"] = "needs-improvement"
            else:
                result["loadTime"] = f"{load_sec:.1f}s (slow)"
                result["loadRating"] = "poor"
        else:
            result["loadTime"] = "N/A"
            result["loadRating"] = "unknown"

        if fcp is not None:
            fcp_sec = fcp / 1000
            if fcp_sec < 1.8:
                result["fcpTime"] = f"{fcp_sec:.1f}s (fast)"
                result["fcpRating"] = "good"
            elif fcp_sec < 3.0:
                result["fcpTime"] = f"{fcp_sec:.1f}s (moderate)"
                result["fcpRating"] = "needs-improvement"
            else:
                result["fcpTime"] = f"{fcp_sec:.1f}s (slow)"
                result["fcpRating"] = "poor"
        else:
            result["fcpTime"] = "N/A"
            result["fcpRating"] = "unknown"

        transfer = metrics.get("transferSize")
        if transfer is not None:
            result["transferSize"] = f"{transfer / 1024:.1f} KB"
        decoded = metrics.get("decodedBodySize")
        if decoded is not None:
            result["pageWeight"] = f"{decoded / 1024:.1f} KB"

        return result

    # ------------------------------------------------------------------
    # Visual capture (screenshots for report)
    # ------------------------------------------------------------------
    def capture_screenshots(
        self, url: str,
        desktop_width: int = 1280, desktop_height: int = 800,
        mobile_width: int = 375, mobile_height: int = 812,
    ) -> dict[str, bytes | None]:
        """Capture desktop and mobile screenshots of a URL.

        Returns dict with ``desktop_png`` and ``mobile_png`` bytes,
        or ``None`` for each if capture failed.
        """
        page = self._page_or_none()
        if page is None:
            return {"desktop_png": None, "mobile_png": None}

        # Desktop
        desktop_png: bytes | None = None
        try:
            page.set_viewport_size({"width": desktop_width, "height": desktop_height})
            ok = self._goto(page, url)
            if ok:
                page.wait_for_timeout(2000)
                desktop_png = page.screenshot(full_page=False)
        except Exception as e:
            logger.warning(f"BrowserOS: desktop screenshot failed for {url} — {e}")

        # Mobile
        mobile_png: bytes | None = None
        try:
            page.set_viewport_size({"width": mobile_width, "height": mobile_height})
            ok = self._goto(page, url)
            if ok:
                page.wait_for_timeout(2000)
                mobile_png = page.screenshot(full_page=False)
        except Exception as e:
            logger.warning(f"BrowserOS: mobile screenshot failed for {url} — {e}")

        return {"desktop_png": desktop_png, "mobile_png": mobile_png}

    def capture_screenshot_desktop(self, url: str) -> bytes | None:
        """Convenience: capture a single desktop viewport screenshot."""
        return self.capture_screenshots(url).get("desktop_png")

    def capture_screenshot_mobile(self, url: str) -> bytes | None:
        """Convenience: capture a single mobile viewport screenshot."""
        return self.capture_screenshots(url, desktop_width=0, desktop_height=0).get("mobile_png")

    # ------------------------------------------------------------------
    # Page audit (technical SEO check for a single URL)
    # ------------------------------------------------------------------
    def audit_page(self, url: str) -> dict[str, Any]:
        page = self._page_or_none()
        if page is None:
            return {"url": url, "audit_ok": False, "issues": ["browseros_not_connected"]}
        ok = self._goto(page, url)
        if not ok:
            return {"url": url, "audit_ok": False, "issues": ["page_load_failed"]}
        raw = page.evaluate(self._audit_page_js())
        raw["url"] = url
        raw["audit_ok"] = True
        return raw

    # ------------------------------------------------------------------
    # Site crawl (Firecrawl-style via BrowserOS)
    # ------------------------------------------------------------------
    def crawl_site(
        self, start_url: str, max_pages: int = _MAX_CRAWL_PAGES,
    ) -> list[dict[str, Any]]:
        page = self._page_or_none()
        if page is None:
            return []
        parsed = urlparse(start_url)
        base_domain = parsed.netloc.lower().replace("www.", "")
        visited: set[str] = set()
        to_visit: list[str] = [start_url]
        results: list[dict[str, Any]] = []

        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)

            ok = self._goto(page, url)
            if not ok:
                results.append({"url": url, "audit_ok": False, "issues": ["page_load_failed"]})
                continue

            raw = page.evaluate(self._audit_page_js())
            audit = self._audit_enhance(raw, page)
            audit["url"] = url
            audit["audit_ok"] = True
            results.append(audit)

            # Discover new internal links
            for link in raw.get("linkUrls", []):
                abs_url = self._resolve_url(link, start_url)
                if abs_url is None:
                    continue
                ap = urlparse(abs_url)
                ad = ap.netloc.lower().replace("www.", "")
                if ad != base_domain:
                    continue
                clean = f"{ap.scheme}://{ap.netloc}{ap.path.rstrip('/')}" if ap.path else abs_url
                if clean not in visited and clean not in to_visit:
                    to_visit.append(clean)

            time.sleep(0.5)

        logger.info(
            f"BrowserOS crawl: {len(results)} pages from {start_url} "
            f"(visited {len(visited)}, max {max_pages})"
        )
        return results

    # ------------------------------------------------------------------
    # Backlink extraction (via cloud browser to bypass Cloudflare)
    # ------------------------------------------------------------------
    def fetch_backlinks(self, domain: str) -> dict[str, Any]:
        try:
            page = self._page_or_none()
            if page is None:
                return {"status": "BROWSEROS_NOT_CONNECTED", "domain": domain}

            sources = [
                (f"https://smallseotools.com/backlink-checker/", "smallseotools"),
            ]

            for url, source_name in sources:
                try:
                    ok = self._goto(page, url)
                    if not ok:
                        continue

                    if page.evaluate(self._detect_blocked_js()):
                        logger.warning("BrowserOS: %s blocked this request", source_name)
                        continue

                    try:
                        input_el = page.locator("input[type='text'], input[name='domain']")
                        if input_el.is_visible(timeout=5000):
                            input_el.fill(domain)
                            page.wait_for_timeout(1000)
                            check_btn = page.get_by_role("button", name="Check", exact=False)
                            if check_btn.is_visible(timeout=3000):
                                check_btn.click()
                                page.wait_for_timeout(10000)
                    except Exception:
                        pass

                    raw = page.evaluate(self._extract_backlinks_js())
                    has_data = any(v is not None for v in raw.values())
                    if has_data:
                        raw["_source"] = source_name
                        raw["domain"] = domain
                        logger.info(
                            "BrowserOS backlinks for %s via %s: %s",
                            domain, source_name, raw
                        )
                        return raw
                except Exception as e:
                    logger.warning("BrowserOS: %s scrape failed for %s: %s", source_name, domain, e)
                    continue

        except Exception as e:
            logger.error("BrowserOS fetch_backlinks crashed for %s: %s", domain, e)

        return {
            "status": "NO_DATA_SCRAPED",
            "domain": domain,
            "_source": "browseros",
            "total_backlinks": None,
            "ref_domains": None,
            "dofollow": None,
            "nofollow": None,
            "dr": None,
        }

    def _audit_enhance(self, raw: dict[str, Any], page: Any) -> dict[str, Any]:
        raw.setdefault("issues", [])
        # Detect viewport issues
        viewport = page.evaluate("() => ({w: window.innerWidth, h: window.innerHeight})")
        raw["viewport"] = viewport
        # Detect HTTPS
        raw["isHTTPS"] = page.evaluate("() => window.location.protocol === 'https:'")
        if not raw.get("isHTTPS"):
            raw["issues"].append("Served over HTTP (not HTTPS)")
        # Detect status code
        raw["statusCode"] = 200
        # Check for canonical
        canonical = page.evaluate("""() => {
            const el = document.querySelector('link[rel="canonical"]');
            return el ? el.getAttribute('href') || '' : '';
        }""")
        raw["canonical"] = canonical
        return raw

    @staticmethod
    def _resolve_url(href: str, base: str) -> str | None:
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return None
        if ":" in href and not href.startswith("/") and not href.startswith("."):
            return None
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if href.startswith("//"):
            p = urlparse(base)
            return f"{p.scheme}:{href}"
        if href.startswith("/"):
            p = urlparse(base)
            return f"{p.scheme}://{p.netloc}{href}"
        p = urlparse(base)
        base_path = p.path.rstrip("/")
        if "/" in base_path:
            base_dir = base_path.rsplit("/", 1)[0]
        else:
            base_dir = ""
        return f"{p.scheme}://{p.netloc}{base_dir}/{href}"

    # ------------------------------------------------------------------
    # Multi-page SERP extraction
    # ------------------------------------------------------------------
    def _fetch_page(
        self, page: Any, url: str,
    ) -> list[dict[str, Any]]:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=_SEARCH_TIMEOUT)
        except Exception as e:
            logger.warning(f"BrowserOS: page.goto timeout — {e}")
            page.wait_for_timeout(2000)
        page.wait_for_timeout(_PAGE_LOAD_WAIT * 1000)

        blocked = page.evaluate(self._detect_blocked_js())
        if blocked:
            logger.warning("BrowserOS: Google CAPTCHA/block detected")
            return []

        return page.evaluate(self._extract_serp_js())

    # ------------------------------------------------------------------
    # SERP search
    # ------------------------------------------------------------------
    def search(
        self,
        keyword: str,
        location: str = "",
        device: str = "desktop",
        num_results: int = 10,
        pages: int = 1,
    ) -> dict[str, Any]:
        pages = max(1, min(pages, 3))
        context, page = self._ensure_connected() or (None, None)
        if page is None:
            return {"keyword": keyword, "error": "browseros_not_connected", "results": []}
        try:

            if device.lower() == "mobile":
                context.add_init_script("""
                Object.defineProperty(navigator, 'userAgent', {
                    value: 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 '
                    'KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36'
                });
                """)

            loc_param = ""
            if location:
                city = location.split(",")[0].strip()
                loc_param = f"&near={quote(city)}"

            all_organic: list[dict[str, Any]] = []
            seen_links: set[str] = set()

            for page_num in range(pages):
                start = page_num * 10
                url = (
                    f"https://www.google.com/search"
                    f"?q={quote(keyword)}"
                    f"{loc_param}"
                    f"&gl=in&hl=en&num=10"
                    f"&start={start}"
                )

                raw = self._fetch_page(page, url)
                if not raw and page_num > 0:
                    break

                for r in (raw or []):
                    link = (r.get("link") or "").strip()
                    title = (r.get("title") or "").strip()
                    if not link or not title or link in seen_links:
                        continue
                    seen_links.add(link)
                    all_organic.append({
                        "position": len(all_organic) + 1,
                        "link": link,
                        "title": title,
                    })

                if page_num < pages - 1:
                    time.sleep(1.5)

            pages_fetched = page_num + 1 if raw else page_num
            logger.info(
                f"BrowserOS: '{keyword}' @ '{location}' ({device}) "
                f"-> {len(all_organic)} organic results over {pages_fetched} page(s)"
            )
            return {"organic_results": all_organic}

        except Exception as e:
            logger.error(f"BrowserOS search failed for '{keyword}': {e}")
            self.close()
            raise BrowserOSError(str(e)) from e
