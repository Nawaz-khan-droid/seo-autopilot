"""Standalone screenshot capture via Playwright."""
from __future__ import annotations

import logging
import time
import urllib.parse

logger = logging.getLogger(__name__)

DESKTOP_WIDTH = 1280
DESKTOP_HEIGHT = 1000


def capture_screenshots(
    url: str,
    desktop_width: int = DESKTOP_WIDTH,
    desktop_height: int = DESKTOP_HEIGHT,
    mobile_width: int = 375,
    mobile_height: int = 812,
    timeout_ms: int = 20000,
) -> dict[str, bytes | None]:
    from playwright.sync_api import sync_playwright

    desktop_png: bytes | None = None
    mobile_png: bytes | None = None

    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": desktop_width, "height": desktop_height},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        except Exception:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception as e:
                logger.warning(f"Screenshot: page load failed for {url} — {e}")
            else:
                page.wait_for_timeout(3000)
        else:
            page.wait_for_timeout(2000)

        try:
            page.set_viewport_size({"width": desktop_width, "height": desktop_height})
            page.wait_for_timeout(500)
            desktop_png = page.screenshot(full_page=False)
        except Exception as e:
            logger.warning(f"Screenshot: desktop capture failed — {e}")

        try:
            context_m = browser.new_context(
                viewport={"width": mobile_width, "height": mobile_height},
                user_agent=(
                    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Mobile Safari/537.36"
                ),
                locale="en-US",
            )
            page_m = context_m.new_page()
            try:
                page_m.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page_m.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Screenshot: mobile page load failed — {e}")
            else:
                mobile_png = page_m.screenshot(full_page=False)
            context_m.close()
        except Exception as e:
            logger.warning(f"Screenshot: mobile capture failed — {e}")

        context.close()
        browser.close()
    except Exception as e:
        logger.error(f"Screenshot: browser launch failed — {e}")
    finally:
        try:
            pw.stop()
        except Exception:
            pass

    return {"desktop_png": desktop_png, "mobile_png": mobile_png}


def capture_pagespeed_insights(
    url: str,
    analysis_timeout_ms: int = 120000,
) -> dict[str, bytes | None]:
    """Capture PSI desktop + mobile screenshots using Playwright.

    Navigates to pagespeed.web.dev, waits for analysis to finish (gauges visible),
    screenshots the .lh-categories results section for both mobile and desktop tabs.
    Uses Shadow DOM aware locators for reliable element detection.
    """
    from playwright.sync_api import sync_playwright

    desktop_png: bytes | None = None
    mobile_png: bytes | None = None
    desktop_score: str | None = None
    mobile_score: str | None = None

    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        psi_url = f"https://pagespeed.web.dev/analysis?url={urllib.parse.quote(url, safe='')}"
        logger.info(f"PSI: navigating to {psi_url}")

        try:
            page.goto(psi_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            logger.warning(f"PSI: initial nav failed — {e}")

        # Wait for analysis to complete — gauge element appears in Shadow DOM
        # Playwright locators automatically pierce Shadow DOM
        gauge_selector = "a.lh-gauge__percentage-slot"
        try:
            page.wait_for_selector(gauge_selector, timeout=analysis_timeout_ms)
            page.wait_for_timeout(3000)
            logger.info("PSI: analysis complete, gauges visible")
        except Exception as e:
            logger.warning(f"PSI: gauges did not appear within timeout — {e}")
            # Try to screenshot whatever loaded
            try:
                desktop_png = page.screenshot(full_page=False)
            except Exception:
                pass
            context.close()
            browser.close()
            pw.stop()
            return {"desktop_png": desktop_png, "mobile_png": mobile_png}

        # Extract mobile score (default view)
        try:
            score_el = page.locator(gauge_selector).first
            if score_el:
                mobile_score = score_el.inner_text(timeout=5000)
                logger.info(f"PSI: mobile score = {mobile_score}")
        except Exception as e:
            logger.warning(f"PSI: could not extract mobile score — {e}")

        # Screenshot the results categories section for mobile
        try:
            categories = page.locator(".lh-categories")
            mobile_png = categories.screenshot(timeout=10000)
            logger.info(f"PSI: mobile category screenshot ({len(mobile_png)} bytes)")
        except Exception as e:
            logger.warning(f"PSI: mobile category screenshot failed — {e}")
            try:
                mobile_png = page.screenshot(full_page=False)
            except Exception:
                pass

        # Switch to Desktop tab — these buttons are in the regular DOM (outside Shadow DOM)
        try:
            desktop_tab = page.locator('button[id="desktop-tab"]')
            if desktop_tab.count() > 0:
                desktop_tab.click()
                page.wait_for_timeout(3000)
                # Wait for desktop gauges to render
                try:
                    page.wait_for_selector(gauge_selector, timeout=60000)
                    page.wait_for_timeout(2000)
                    logger.info("PSI: desktop results loaded")
                except Exception:
                    pass

                # Extract desktop score
                try:
                    score_el = page.locator(gauge_selector).first
                    if score_el:
                        desktop_score = score_el.inner_text(timeout=5000)
                        logger.info(f"PSI: desktop score = {desktop_score}")
                except Exception as e:
                    logger.warning(f"PSI: could not extract desktop score — {e}")

                # Screenshot desktop categories
                try:
                    categories = page.locator(".lh-categories")
                    desktop_png = categories.screenshot(timeout=10000)
                    logger.info(f"PSI: desktop category screenshot ({len(desktop_png)} bytes)")
                except Exception as e:
                    logger.warning(f"PSI: desktop category screenshot failed — {e}")
                    try:
                        desktop_png = page.screenshot(full_page=False)
                    except Exception:
                        pass
            else:
                logger.warning("PSI: desktop tab button not found, taking full-page screenshot")
                desktop_png = page.screenshot(full_page=False)
        except Exception as e:
            logger.warning(f"PSI: desktop tab switch failed — {e}")
            try:
                desktop_png = page.screenshot(full_page=False)
            except Exception:
                pass

        context.close()
        browser.close()
    except Exception as e:
        logger.error(f"PSI: browser launch failed — {e}")
    finally:
        try:
            pw.stop()
        except Exception:
            pass

    return {
        "desktop_png": desktop_png,
        "mobile_png": mobile_png,
        "desktop_score": desktop_score,
        "mobile_score": mobile_score,
    }
