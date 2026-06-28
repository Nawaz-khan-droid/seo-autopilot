from __future__ import annotations

import logging
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


class SearchConsoleClient:
    def __init__(self, credentials_path: str, site_url: str) -> None:
        self.site_url = site_url
        self.service = None

        if not site_url:
            logger.info("GSC: No site_url configured — skipping")
            return

        try:
            creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=SCOPES
            )
            self.service = build(
                "searchconsole", "v1", credentials=creds, cache_discovery=False
            )
            logger.info(f"GSC: initialized for {site_url}")
        except Exception as e:
            logger.warning(f"GSC: init failed — {e}")

    def query(
        self,
        start_date: str,
        end_date: str,
        row_limit: int = 10,
    ) -> dict[str, Any]:
        if not self.service:
            return {
                "status": "skipped",
                "note": "GSC not configured — set GSC_SITE_URL and grant access",
            }

        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query"],
            "rowLimit": row_limit,
        }

        try:
            response = (
                self.service.searchanalytics()
                .query(siteUrl=self.site_url, body=body)
                .execute()
            )
            rows = response.get("rows", [])
            total_clicks = sum(r.get("clicks", 0) for r in rows)
            total_impressions = sum(r.get("impressions", 0) for r in rows)
            logger.info(
                f"GSC: {len(rows)} queries, "
                f"{total_clicks} clicks, {total_impressions} impressions"
            )
            return {
                "status": "ok",
                "rows": rows,
                "total_clicks": total_clicks,
                "total_impressions": total_impressions,
            }
        except HttpError as e:
            if e.resp.status in (401, 403):
                msg = (
                    "Access Required — add the service account email to your "
                    "GSC property as a user"
                )
                logger.warning(f"GSC: {msg}")
                return {"status": "access_denied", "note": msg}
            logger.error(f"GSC: HTTP {e.resp.status} — {e}")
            return {"status": "error", "note": str(e)}
        except Exception as e:
            logger.error(f"GSC: query failed — {e}", exc_info=True)
            return {"status": "error", "note": str(e)}
