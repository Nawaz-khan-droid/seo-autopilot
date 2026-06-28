from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


class AnalyticsClient:
    def __init__(self, credentials_path: str, property_id: str) -> None:
        self.property_id = property_id
        self.client = None
        self._enabled = bool(property_id)

        if not self._enabled:
            logger.info("GA4: no property ID configured — skipping")
            return

        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            self.client = BetaAnalyticsDataClient(credentials=creds)
            logger.info(f"GA4: initialized for property {property_id}")
        except ImportError:
            logger.warning(
                "GA4: google-analytics-data package not installed — skipping"
            )
        except Exception as e:
            logger.warning(f"GA4: init failed — {e}")

    def get_metrics(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        if not self._enabled or not self.client:
            return {
                "organic_users": "Access Required",
                "sessions": "Access Required",
                "engaged_sessions": "Access Required",
            }

        try:
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Metric,
                RunReportRequest,
            )

            today = date.today()
            sd = start_date or today.replace(day=1).isoformat()
            ed = end_date or today.isoformat()

            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date=sd, end_date=ed)],
                dimensions=[Dimension(name="sessionDefaultChannelGrouping")],
                metrics=[
                    Metric(name="totalUsers"),
                    Metric(name="sessions"),
                    Metric(name="engagedSessions"),
                ],
            )
            response = self.client.run_report(request)

            organic_users = 0
            sessions = 0
            engaged_sessions = 0

            for row in response.rows:
                channel = row.dimension_values[0].value.lower()
                if "organic" in channel:
                    organic_users += int(row.metric_values[0].value or 0)
                    sessions += int(row.metric_values[1].value or 0)
                    engaged_sessions += int(row.metric_values[2].value or 0)

            logger.info(
                f"GA4: {organic_users} organic users, "
                f"{sessions} sessions, {engaged_sessions} engaged"
            )
            return {
                "organic_users": organic_users,
                "sessions": sessions,
                "engaged_sessions": engaged_sessions,
            }

        except Exception as e:
            logger.warning(f"GA4: query failed — {e}", exc_info=True)
            return {
                "organic_users": "Access Required",
                "sessions": "Access Required",
                "engaged_sessions": "Access Required",
            }
