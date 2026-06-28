from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from modules.browseros_client import BrowserOSClient
from modules.ga4_client import AnalyticsClient
from modules.pagespeed import PageSpeedClient
from modules.search_console import SearchConsoleClient
from modules.sheet_client import SheetClient

logger = logging.getLogger(__name__)

# Phase 1 schema: 5 columns only. CTR was removed (derived metric,
# requires GA4 data which is currently unavailable).
INSIGHTS_HEADERS = [
    "URL",
    "Mobile PSI",
    "Desktop PSI",
    "Clicks",
    "Impressions",
]

# Extended schema when BrowserOS page speed is available
INSIGHTS_EXTENDED_HEADERS = [
    "URL",
    "Mobile PSI",
    "Desktop PSI",
    "BrowserOS Load Time",
    "BrowserOS FCP",
    "BrowserOS Page Weight",
    "Clicks",
    "Impressions",
]

# Source-group semantics: when a data source fails, ALL cells in that
# group share the same "Access Required" value. We never mix real
# numbers with "Access Required" inside a single source group.
GSC_ACCESS_REQUIRED = "Access Required"
PSI_NOT_AVAILABLE = "N/A"


class WebsiteInsightsWorkflow:
    def __init__(
        self,
        sheet: SheetClient,
        pagespeed: PageSpeedClient,
        browseros: BrowserOSClient | None = None,
        gsc: SearchConsoleClient | None = None,
        analytics: AnalyticsClient | None = None,
    ) -> None:
        self.sheet = sheet
        self.pagespeed = pagespeed
        self.browseros = browseros
        self.gsc = gsc
        self.analytics = analytics

    def _browseros_page_speed(self, url: str) -> dict[str, Any]:
        if not self.browseros:
            return {}
        try:
            metrics = self.browseros.measure_performance(url)
            return self.browseros.summarize_performance(metrics)
        except Exception as e:
            logger.warning(f"BrowserOS page speed fallback failed for {url}: {e}")
            return {}

    def _build_insights_row(
        self,
        url: str,
        ps: dict[str, Any],
        gsc_data: dict[str, Any],
        bro_metrics: dict[str, Any] | None = None,
    ) -> list[Any]:
        mobile = ps.get("mobile")
        desktop = ps.get("desktop")

        # --- PageSpeed group: both cells always match ---
        if mobile is None and desktop is None:
            mobile_value: Any = PSI_NOT_AVAILABLE
            desktop_value: Any = PSI_NOT_AVAILABLE
        else:
            mobile_value = str(round(mobile, 1)) if mobile is not None else PSI_NOT_AVAILABLE
            desktop_value = str(round(desktop, 1)) if desktop is not None else PSI_NOT_AVAILABLE

        # --- GSC group: both cells always match ---
        # If gsc is unavailable OR gsc query failed OR status != ok,
        # BOTH clicks and impressions are "Access Required".
        # We never put 0 in one and "Access Required" in the other.
        if gsc_data.get("status") == "ok":
            clicks: Any = gsc_data.get("total_clicks", GSC_ACCESS_REQUIRED)
            impressions: Any = gsc_data.get("total_impressions", GSC_ACCESS_REQUIRED)
        else:
            clicks = GSC_ACCESS_REQUIRED
            impressions = GSC_ACCESS_REQUIRED

        return [
            url,
            mobile_value,
            desktop_value,
            clicks,
            impressions,
        ]

    def run(self, keywords: list[dict[str, Any]] | None = None) -> list[list[Any]]:
        if keywords is None:
            keywords_ws = self.sheet.get_tab("Keywords")
            keywords = keywords_ws.get_all_records()

        unique_urls: list[str] = []
        seen: set[str] = set()
        for row in keywords:
            url = str(row.get("Target URL", "") or "").strip()
            if url and url not in seen:
                seen.add(url)
                unique_urls.append(url)

        headers = list(INSIGHTS_EXTENDED_HEADERS) if self.browseros else list(INSIGHTS_HEADERS)
        output: list[list[Any]] = [headers]

        for url in unique_urls:
            logger.info(f"Website insights: collecting data for {url}")

            ps = self.pagespeed.analyze_both(url)

            # BrowserOS fallback if PageSpeed API failed (429/error)
            bro_metrics: dict[str, Any] | None = None
            if self.browseros and (ps.get("mobile") is None or ps.get("desktop") is None):
                bro_metrics = self._browseros_page_speed(url)
                logger.info(
                    f"BrowserOS page speed fallback for {url}: "
                    f"load={bro_metrics.get('loadTime','N/A')} "
                    f"fcp={bro_metrics.get('fcpTime','N/A')}"
                )

            # GSC group: query the whole month once. If anything fails,
            # both Clicks and Impressions become "Access Required".
            gsc_data: dict[str, Any] = {"status": "skipped"}
            if self.gsc:
                end = datetime.now().strftime("%Y-%m-%d")
                start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
                try:
                    gsc_data = self.gsc.query(start_date=start, end_date=end)
                except Exception as e:
                    logger.warning(f"GSC query failed for {url}: {e}")
                    gsc_data = {"status": "error"}

            row = self._build_insights_row(
                url=url, ps=ps, gsc_data=gsc_data, bro_metrics=bro_metrics,
            )

            # Append BrowserOS columns when available
            if bro_metrics:
                row.append(bro_metrics.get("loadTime", "N/A"))
                row.append(bro_metrics.get("fcpTime", "N/A"))
                row.append(bro_metrics.get("pageWeight", "N/A"))

            output.append(row)

        if len(output) > 1:
            try:
                self.sheet.write_rows("Website Tracking & Insights", output)
                logger.info(
                    f"Website Insights: wrote {len(output) - 1} rows for "
                    f"{len(unique_urls)} unique URLs"
                )
            except Exception as e:
                logger.error(
                    f"Website Insights row write FAILED: {e}", exc_info=True
                )
                raise

        return output
