from __future__ import annotations

import logging
import time
from typing import Any

import requests
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

PAGESPEED_BASE_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PAGESPEED_SCOPE = "https://www.googleapis.com/auth/pagespeed.readonly"
CLOUD_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class PageSpeedClient:
    def __init__(self, api_key: str = "", credentials_path: str = "") -> None:
        self.api_key = api_key
        self._auth_token: str | None = None
        self._last_request_time: float = 0.0
        if credentials_path:
            self._acquire_token(credentials_path)

    def _acquire_token(self, credentials_path: str) -> None:
        try:
            creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=[CLOUD_SCOPE]
            )
            creds.refresh(AuthRequest())
            if creds.token:
                self._auth_token = creds.token
                logger.info("PageSpeed: service account token acquired")
        except Exception as e:
            logger.warning(f"PageSpeed: token acquisition failed — {e}")

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < 0.35:
            time.sleep(0.35 - elapsed)

    def _do_request(
        self, url: str, strategy: str,
        api_key: str = "", token: str | None = None,
    ) -> requests.Response:
        params: dict[str, str] = {"url": url, "strategy": strategy}
        headers: dict[str, str] = {}
        if api_key:
            params["key"] = api_key
        elif token:
            headers["Authorization"] = f"Bearer {token}"
        return requests.get(
            PAGESPEED_BASE_URL, params=params, headers=headers, timeout=30,
        )

    def _run_strategy(self, url: str, strategy: str) -> dict[str, Any]:
        self._rate_limit()

        # Priority: API key > OAuth token > unauthenticated
        strategies: list[tuple[str, str | None, str]] = []
        if self.api_key:
            strategies.append(("API key", self.api_key, None))
        if self._auth_token:
            strategies.append(("OAuth token", "", self._auth_token))
        strategies.append(("unauthenticated", "", None))

        last_exc: Exception | None = None
        for label, key, token in strategies:
            try:
                response = self._do_request(url, strategy, api_key=key, token=token)
                if response.status_code in (401, 403):
                    logger.debug(
                        f"PageSpeed ({strategy}): {label} → {response.status_code}, "
                        f"trying next auth method"
                    )
                    last_exc = requests.HTTPError(response.status_code, response=response)
                    continue
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = int(retry_after) if retry_after and retry_after.isdigit() else 15
                    logger.warning(
                        f"PageSpeed ({strategy}): 429 rate limited — "
                        f"Retry-After={wait}s, waiting..."
                    )
                    time.sleep(wait)
                    self._rate_limit()
                    response = self._do_request(url, strategy, api_key=key, token=token)
                    if response.status_code == 429:
                        last_exc = requests.HTTPError(429, response=response)
                        continue
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                last_exc = e
                continue

        raise last_exc or requests.ConnectionError("All auth strategies failed")

    def analyze(self, url: str, strategy: str = "mobile") -> float | None:
        try:
            data = self._run_strategy(url, strategy)
            score = (
                data.get("lighthouseResult", {})
                .get("categories", {})
                .get("performance", {})
                .get("score")
            )
            if score is not None:
                score = round(score * 100, 1)
                logger.info(f"PageSpeed ({strategy}) for {url}: {score}")
                return score
            logger.warning(
                f"PageSpeed ({strategy}) for {url}: no score in response"
            )
            return None
        except requests.RequestException as e:
            logger.warning(
                f"PageSpeed ({strategy}) for {url}: {e}",
                exc_info=True,
            )
            return None
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(
                f"PageSpeed ({strategy}) for {url}: unexpected response "
                f"structure - {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.warning(
                f"PageSpeed ({strategy}) for {url}: unexpected error - {e}",
                exc_info=True,
            )
            return None

    def analyze_both(self, url: str) -> dict[str, float | None]:
        return {
            "mobile": self.analyze(url, "mobile"),
            "desktop": self.analyze(url, "desktop"),
        }

    def analyze_cwv(self, url: str, strategy: str = "mobile") -> dict[str, Any]:
        """Extract full Core Web Vitals data from PageSpeed API response.
        
        Returns dict with keys: score, lcp_seconds, inp_ms, cls_score,
        render_blocking_ms, tbt_ms. Each value is float or None.
        """
        try:
            data = self._run_strategy(url, strategy)
            lr = data.get("lighthouseResult", {})
            audits = lr.get("audits", {})
            categories = lr.get("categories", {})

            score = None
            perf = categories.get("performance", {})
            if perf.get("score") is not None:
                score = round(perf["score"] * 100, 1)

            lcp_ms = None
            lcp_audit = audits.get("largest-contentful-paint", {})
            if lcp_audit.get("numericValue") is not None:
                lcp_ms = round(lcp_audit["numericValue"] / 1000, 2)

            inp_ms = None
            inp_audit = audits.get("interaction-to-next-paint", {})
            if inp_audit.get("numericValue") is not None:
                inp_ms = round(inp_audit["numericValue"], 1)

            cls = None
            cls_audit = audits.get("cumulative-layout-shift", {})
            if cls_audit.get("numericValue") is not None:
                cls = round(cls_audit["numericValue"], 3)

            render_blocking_ms = None
            rb_audit = audits.get("render-blocking-resources", {})
            if rb_audit.get("numericValue") is not None:
                render_blocking_ms = round(rb_audit["numericValue"], 1)

            tbt_ms = None
            tbt_audit = audits.get("total-blocking-time", {})
            if tbt_audit.get("numericValue") is not None:
                tbt_ms = round(tbt_audit["numericValue"], 1)

            return {
                "score": score,
                "lcp_seconds": lcp_ms,
                "inp_ms": inp_ms,
                "cls_score": cls,
                "render_blocking_ms": render_blocking_ms,
                "tbt_ms": tbt_ms,
            }
        except requests.RequestException as e:
            logger.warning(f"PageSpeed CWV ({strategy}) for {url}: {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.warning(f"PageSpeed CWV ({strategy}) for {url}: unexpected error - {e}", exc_info=True)
            return {}

    def analyze_cwv_both(self, url: str) -> dict[str, dict[str, Any]]:
        return {
            "mobile": self.analyze_cwv(url, "mobile"),
            "desktop": self.analyze_cwv(url, "desktop"),
        }
