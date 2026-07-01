from __future__ import annotations

import logging
import os
import random
import threading
from typing import Any
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = None  # type: ignore[assignment]
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)

BROWSER_PROXY_URL = os.environ.get("BROWSER_PROXY_URL", "")

_STEALTH_HOOK = None
STEALTH_AVAILABLE = False
try:
    from playwright_stealth import Stealth as _Stealth
    _STEALTH_HOOK = _Stealth(
        navigator_webdriver=True,
        webgl_vendor=True,
        navigator_platform=True,
        chrome_runtime=True,
        navigator_languages=True,
        media_codecs=True,
        hairline=True,
    )
    STEALTH_AVAILABLE = True
    logger.info("playwright-stealth available — browser fingerprint masking enabled")
except ImportError:
    logger.info("playwright-stealth not installed — browser fingerprint masking disabled")

_PLAYWRIGHT_TLS = threading.local()

_ACTIVE_BROWSER_THREAD_IDS: set[int] = set()
_BROWSER_LOCK = threading.Lock()


def _get_pw() -> tuple[Any, Any]:
    if not hasattr(_PLAYWRIGHT_TLS, "pw"):
        _PLAYWRIGHT_TLS.pw = None
        _PLAYWRIGHT_TLS.browser = None
    return _PLAYWRIGHT_TLS.pw, _PLAYWRIGHT_TLS.browser


def _set_pw(pw, browser) -> None:
    _PLAYWRIGHT_TLS.pw = pw
    _PLAYWRIGHT_TLS.browser = browser


def _secure_context(browser, **overrides) -> tuple[Any, Any]:
    vp_w = 1280 + random.randint(-3, 3)
    vp_h = 720 + random.randint(-3, 3)
    caller_viewport = overrides.pop("viewport", None)
    ctx_kwargs = dict(
        viewport=caller_viewport or {"width": vp_w, "height": vp_h},
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"),
        locale="en-US",
        timezone_id="America/New_York",
        permissions=[],
        storage_state=None,
        reduced_motion="no-preference",
        device_scale_factor=1.0,
        has_touch=False,
        is_mobile=False,
    )
    ctx_kwargs.update(overrides)
    context = browser.new_context(**ctx_kwargs)
    page = context.new_page()
    return context, page


def _get_browser_page(**kwargs):
    pw, browser = _get_pw()

    launch_kwargs: dict[str, Any] = dict(
        headless=True,
        args=[
            "--disable-extensions",
            "--disable-notifications",
            "--disable-background-networking",
            "--disable-sync",
            "--no-first-run",
            "--disable-component-update",
        ],
    )
    if BROWSER_PROXY_URL:
        proxy_config: dict[str, str] = {"server": BROWSER_PROXY_URL}
        if "@" in BROWSER_PROXY_URL:
            parsed = urlparse(BROWSER_PROXY_URL)
            if parsed.username and parsed.password:
                proxy_config["username"] = parsed.username
                proxy_config["password"] = parsed.password
                proxy_config["server"] = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        launch_kwargs["proxy"] = proxy_config
        logger.info("Playwright proxy configured: %s", proxy_config["server"])

    if browser is None:
        try:
            if pw is None:
                pw = sync_playwright().start()
            browser = pw.chromium.launch(**launch_kwargs)
            _set_pw(pw, browser)
            _ACTIVE_BROWSER_THREAD_IDS.add(threading.current_thread().ident)
        except Exception as e:
            logger.warning("Playwright thread launch failed: %s", e)
            return None
    else:
        try:
            if not browser.is_connected():
                logger.info("Browser disconnected — re-launching for thread %s",
                            threading.current_thread().name)
                try:
                    browser.close()
                except Exception:
                    pass
                browser = None
                _PLAYWRIGHT_TLS.browser = None
        except Exception:
            browser = None
            _PLAYWRIGHT_TLS.browser = None

    if browser is None:
        try:
            if pw is None:
                pw = sync_playwright().start()
            browser = pw.chromium.launch(**launch_kwargs)
            _set_pw(pw, browser)
            _ACTIVE_BROWSER_THREAD_IDS.add(threading.current_thread().ident)
        except Exception as e:
            logger.warning("Playwright re-launch failed for thread %s: %s",
                           threading.current_thread().name, e)
            return None
    try:
        ctx, page = _secure_context(browser, **kwargs)
        original_close = page.close

        def _close_with_cleanup():
            try:
                ctx.close()
            except Exception:
                pass
            try:
                original_close()
            except Exception:
                pass
        page.close = _close_with_cleanup
        return page
    except Exception as e:
        logger.warning("Playwright new_page failed: %s", e)
        return None


def _close_browser() -> None:
    pw, browser = _get_pw()
    if browser is not None:
        try:
            browser.close()
        except Exception:
            pass
        _PLAYWRIGHT_TLS.browser = None
    if pw is not None:
        try:
            pw.stop()
        except Exception:
            pass
        _PLAYWRIGHT_TLS.pw = None
    _ACTIVE_BROWSER_THREAD_IDS.discard(threading.current_thread().ident)
    logger.debug("Playwright closed for thread %s", threading.current_thread().name)


def close_all_browsers() -> None:
    """Close Playwright browsers from all tracked threads.
    Live threads self-clean on request end; dead threads are cleaned by OS."""
    with _BROWSER_LOCK:
        thread_ids = list(_ACTIVE_BROWSER_THREAD_IDS)
        _ACTIVE_BROWSER_THREAD_IDS.clear()
    alive = {t.ident for t in threading.enumerate() if t.ident in thread_ids}
    dead = [tid for tid in thread_ids if tid not in alive]
    for tid in dead:
        logger.debug("Thread %s already dead — browser will be cleaned by OS", tid)
    for tid in alive:
        logger.info("Skipping alive thread %s — browser will self-close on request end", tid)
    _close_browser()
