from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from config.location_map import normalize_location
from config.serp_config import (
    APIFY_CONFIG,
    FEATURE_NA,
    FEATURE_NO,
    FEATURE_YES,
    PROVIDER_BREAKER_THRESHOLD,
    RANK_PROVIDERS,
    provider_display_name,
)
from modules.apify_client import ApifyClient, ApifyError
from modules.browseros_client import BrowserOSClient
from modules.searchapi_client import SearchApiClient
from modules.serp_client import SerpClient
from modules.sheet_client import SheetClient
from modules.url_utils import exact_url_match

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SERP Snapshot tab — internal AI dataset
# ---------------------------------------------------------------------------
# Static columns first, then everything that is updated each run.
# Local Maps and Paid Ads were removed from the active schema (probe
# confirmed the actor does not return them). Raw SERP Status was
# removed because it was redundant with the breaker logging.
SERP_HEADERS = [
    "Keyword",                  # static
    "Target URL",               # static
    "Search Location",          # static
    "Device",                   # static
    "Run Date",                 # updated each run
    "Position",                 # updated each run
    "Ranking URL",              # updated each run
    "AI Overview Mention",      # updated each run (YES/NO/N/A)
    "PAA Mention",              # updated each run (YES/NO/N/A)
    "Data Availability",        # updated each run
]

# ---------------------------------------------------------------------------
# SERP display tab — human dashboard
# ---------------------------------------------------------------------------
# 5 static metadata columns + N date columns appended at the right.
SERP_DISPLAY_STATIC_HEADERS = [
    "Keyword",
    "Target URL",
    "Search Location",
    "Device",
    "Search Intent",
]

# SERP History — append-only, 4 columns
HISTORY_TAB = "SERP History"
HISTORY_HEADERS = ["Timestamp", "Keyword", "Position", "Ranking URL"]

# Competitor Snapshot — 9 columns, in-place update
COMPETITOR_TAB = "Competitor Snapshot"
COMPETITOR_HEADERS = [
    "Keyword", "Target URL", "Search Location", "Device",
    "Ranking URL", "Top 1", "Top 2", "Top 3", "Last Updated",
]
SERP_DISPLAY_TAB = "SERP"
SERP_SNAPSHOT_TAB = "SERP Snapshot"

# ISO date format for SERP display tab date columns
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class ProviderHardError(Exception):
    """Auth, quota, or unrecoverable provider error.

    The workflow breaker counts these and skips the provider after
    PROVIDER_BREAKER_THRESHOLD consecutive occurrences.
    """


class SerpTabSchemaError(Exception):
    """Raised when the SERP display tab's static headers are missing or
    out of order. The run aborts — no silent append to a malformed tab."""


class DuplicateDateColumnError(Exception):
    """Raised when two columns in the SERP tab normalize to the same ISO
    date. The run aborts to prevent overwriting a valid date column."""


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
class SerpSnapshotWorkflow:
    def __init__(
        self,
        sheet: SheetClient,
        serp: SerpClient,
        max_keywords: int = 3,
        searchapi: SearchApiClient | None = None,
        apify: ApifyClient | None = None,
        browseros: BrowserOSClient | None = None,
        keywords: list[dict[str, Any]] | None = None,
        provider_order: list[str] | None = None,
    ) -> None:
        self.sheet = sheet
        self.serp = serp
        self.max_keywords = max_keywords
        self.searchapi = searchapi
        self.apify = apify
        self.browseros = browseros
        self.keywords = keywords  # optional pre-loaded keywords
        self.provider_order = provider_order or list(RANK_PROVIDERS)
        # Remove providers whose client is None
        self.provider_order = [p for p in self.provider_order if self._client_available(p)]
        if not self.provider_order:
            logger.warning("No SERP providers available — rank detection will yield Not Found for all keywords")
        # Per-provider hard-error breaker state
        self._breaker: dict[str, int] = {p: 0 for p in self.provider_order}
        self._provider_open: set[str] = set()

    # -----------------------------------------------------------------
    # SERP History archive (called at the start of run())
    # -----------------------------------------------------------------
    def _persist_history(self) -> None:
        try:
            ws = self.sheet.get_tab(SERP_SNAPSHOT_TAB)
            existing = ws.get_all_values()
            if len(existing) <= 1:
                return
            history_ws = self.sheet.get_or_create_tab(HISTORY_TAB, rows=2000, cols=20)
            history_existing = history_ws.get_all_values()
            # Ensure header row exists
            if not history_existing or history_existing[0] != SERP_HEADERS:
                history_ws.clear()
                history_ws.update(range_name="A1", values=[SERP_HEADERS])
            # Append only the last data rows from the current snapshot
            history_ws.append_rows(
                values=existing[1:],
                value_input_option="USER_ENTERED",
            )
            logger.info(
                f"Archived {len(existing) - 1} rows to '{HISTORY_TAB}'"
            )
        except Exception as e:
            logger.warning(f"Could not persist SERP history: {e}")

    # -----------------------------------------------------------------
    # SERP display tab — date-column logic with validation
    # -----------------------------------------------------------------
    def _validate_serp_tab_static_headers(self, header_row: list[str]) -> None:
        """Fail loud when the 5 static headers are missing or out of order.

        The SERP tab is the human dashboard — silent data misalignment
        here is worse than aborting the run.
        """
        if len(header_row) < 5:
            raise SerpTabSchemaError(
                f"SERP tab has only {len(header_row)} static columns; "
                f"expected at least 5. Headers seen: {header_row!r}"
            )
        actual = header_row[:5]
        if actual != SERP_DISPLAY_STATIC_HEADERS:
            raise SerpTabSchemaError(
                f"SERP tab static headers mismatch.\n"
                f"  Expected: {SERP_DISPLAY_STATIC_HEADERS}\n"
                f"  Got:      {actual}\n"
                f"  Please manually re-shape the SERP tab to the approved "
                f"schema before running again."
            )

    def _find_or_append_date_column(
        self, ws: Any, header_row: list[str], date_row: list[str], date_label: str,
    ) -> int:
        """Returns the column index (0-based) for `date_label`.

        Behavior:
        - Normalize each existing date cell (strip whitespace) before compare.
        - If two columns normalize to the same value → DuplicateDateColumnError.
        - If no match → append a new column at the right (Option A).
        - If any non-ISO value appears in a "date" position, log a warning
          and skip it (do not treat as a date column).
        """
        seen_dates: dict[str, int] = {}
        for i in range(5, len(date_row)):
            normalized = date_row[i].strip()
            if not normalized:
                continue
            if not ISO_DATE_RE.match(normalized):
                logger.warning(
                    f"SERP tab: column index {i} has non-ISO value "
                    f"{date_row[i]!r}; treating as a non-date column."
                )
                continue
            if normalized in seen_dates:
                raise DuplicateDateColumnError(
                    f"SERP tab has two columns that normalize to the same "
                    f"date {normalized!r}: columns at index "
                    f"{seen_dates[normalized]} and {i}. "
                    f"Please remove the duplicate manually before rerunning."
                )
            seen_dates[normalized] = i
            if normalized == date_label:
                return i

        # Not found — append at the rightmost position
        new_idx = len(header_row)
        ws.update_cell(1, new_idx + 1, "Rank")
        ws.update_cell(2, new_idx + 1, date_label)
        return new_idx

    def _update_serp_tab(
        self,
        rank_entries: list[dict[str, Any]],
        date_label: str,
    ) -> None:
        """Write ranks as a new date column in the SERP display tab."""
        try:
            ws = self.sheet.get_or_create_tab(SERP_DISPLAY_TAB, rows=200, cols=30)
            existing = ws.get_all_values()

            if not existing or len(existing) < 2:
                # First run — write metadata columns + first rank column
                headers = list(SERP_DISPLAY_STATIC_HEADERS) + ["Rank"]
                date_row = [""] * 5 + [date_label]
                data_rows = []
                for entry in rank_entries:
                    data_rows.append([
                        entry["keyword"],
                        entry["target_url"],
                        entry["location"],
                        entry["device"],
                        entry.get("search_intent", ""),
                        entry["position"],
                    ])
                ws.update(range_name="A1", values=[headers, date_row] + data_rows)
                self._format_serp_tab(ws, len(headers), len(data_rows) + 2)
                logger.info(f"SERP tab: initialized with {len(data_rows)} rows")
                return

            # Validate static headers before any write — fail loud on mismatch
            self._validate_serp_tab_static_headers(existing[0])
            header_row = existing[0]
            date_row = existing[1] if len(existing) > 1 else []

            # Find or append today's date column
            date_col_idx = self._find_or_append_date_column(
                ws, header_row, date_row, date_label
            )

            # Build keyword→position lookup
            kw_positions: dict[str, str] = {}
            for entry in rank_entries:
                key = (
                    f"{entry['keyword'].strip().lower()}|"
                    f"{entry['target_url'].strip().lower()}"
                )
                kw_positions[key] = entry["position"]

            # Batch update the date column — one API call instead of N
            col_letter = self._col_letter(date_col_idx + 1)
            col_values: list[list[str]] = []
            update_count = 0
            for i in range(2, len(existing)):
                row_data = existing[i]
                if len(row_data) < 2:
                    col_values.append([""])
                    continue
                kw = (row_data[0] or "").strip().lower()
                url = (row_data[1] or "").strip().lower() if len(row_data) > 1 else ""
                key = f"{kw}|{url}"
                pos = kw_positions.get(key, "")
                col_values.append([pos])
                if pos:
                    update_count += 1

            if col_values:
                start_row = 3
                end_row = start_row + len(col_values) - 1
                ws.update(
                    range_name=f"{col_letter}{start_row}:{col_letter}{end_row}",
                    values=col_values,
                )

            self._format_serp_tab(ws, date_col_idx + 1, len(existing))
            logger.info(
                f"SERP tab: updated column '{date_label}' "
                f"({update_count} ranks)"
            )
        except (SerpTabSchemaError, DuplicateDateColumnError):
            raise
        except Exception as e:
            logger.warning(f"Could not update SERP tab: {e}")

    @staticmethod
    def _col_letter(n: int) -> str:
        letters = []
        while n > 0:
            n, rem = divmod(n - 1, 26)
            letters.append(chr(65 + rem))
        return "".join(reversed(letters))

    def _format_serp_tab(self, ws: Any, total_cols: int, total_rows: int) -> None:
        """Apply color formatting to SERP tab cells."""
        try:
            rank_color = {"backgroundColor": {"red": 1.0, "green": 0.898, "blue": 0.6}}
            date_color = {"backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.0}}
            bold_arial = {
                "textFormat": {
                    "fontFamily": "Arial",
                    "bold": True,
                }
            }

            if total_cols > 5:
                col = self._col_letter(total_cols)
                ws.format(f"{col}2", {**date_color, **bold_arial})

            if total_rows > 2 and total_cols > 5:
                col = self._col_letter(total_cols)
                ws.format(f"{col}3:{col}{total_rows + 1}", {**rank_color, **bold_arial})
        except Exception as e:
            logger.debug(f"SERP tab formatting skipped: {e}")

    # -----------------------------------------------------------------
    # Competitor Snapshot — in-place update
    # -----------------------------------------------------------------
    def _update_competitor_snapshot(
        self,
        entries: list[dict[str, Any]],
    ) -> None:
        try:
            ws = self.sheet.get_or_create_tab(COMPETITOR_TAB, rows=200, cols=20)
            existing = ws.get_all_values()

            today = datetime.now().strftime("%Y-%m-%d")
            rows_out: list[list[Any]] = [list(COMPETITOR_HEADERS)]

            for entry in entries:
                competitors = entry.get("competitors", [])
                rows_out.append([
                    entry["keyword"],
                    entry["target_url"],
                    entry["location"],
                    entry["device"],
                    entry["ranking_url"],
                    competitors[0] if len(competitors) > 0 else "",
                    competitors[1] if len(competitors) > 1 else "",
                    competitors[2] if len(competitors) > 2 else "",
                    today,
                ])

            if len(rows_out) <= 1:
                return

            if len(existing) >= 2 and len(existing[0]) >= 5:
                for new_row in rows_out[1:]:
                    kw = str(new_row[0]).strip().lower()
                    url = str(new_row[1]).strip().lower()
                    for i in range(1, len(existing)):
                        old = existing[i]
                        if (str(old[0]).strip().lower() == kw
                                and str(old[1]).strip().lower() == url):
                            start_col = self._col_letter(5)
                            end_col = self._col_letter(9)
                            ws.update(
                                range_name=f"{start_col}{i + 1}:{end_col}{i + 1}",
                                values=[new_row[4:9]],
                            )
                            break
                logger.info(
                    f"Competitor Snapshot: updated {len(rows_out) - 1} rows in-place"
                )
            else:
                ws.clear()
                ws.update(range_name="A1", values=rows_out)
                logger.info(
                    f"Competitor Snapshot: initialized with "
                    f"{len(rows_out) - 1} rows"
                )
        except Exception as e:
            logger.warning(f"Could not update Competitor Snapshot: {e}")

    # -----------------------------------------------------------------
    # Error classification
    # -----------------------------------------------------------------
    @staticmethod
    def _classify_error(exc: Exception) -> str:
        """Classify an exception as 'hard' or 'recoverable'.

        Hard errors trip the per-provider breaker. Recoverable errors
        are retried by the provider's own tenacity config and are NOT
        counted by the breaker.
        """
        msg = str(exc).lower()
        # Hard — auth/quota/payload
        hard_signals = (
            "401", "403", "429", "unauthorized", "forbidden",
            "quota", "rate limit", "invalid api key", "invalid_apikey",
            "invalidapikey", "apikeyerror", "authentication",
            "subscription", "billing", "api key", "permission",
        )
        if any(s in msg for s in hard_signals):
            return "hard"
        return "recoverable"

    def _record_hard_error(self, provider: str) -> None:
        self._breaker[provider] = self._breaker.get(provider, 0) + 1
        if (
            self._breaker[provider] >= PROVIDER_BREAKER_THRESHOLD
            and provider not in self._provider_open
        ):
            self._provider_open.add(provider)
            logger.critical(
                f"PROVIDER_BREAKER_OPEN: {provider_display_name(provider)} "
                f"returned {self._breaker[provider]} hard errors, "
                f"skipping for remainder of run"
            )

    def _client_available(self, provider: str) -> bool:
        if provider == "serpapi":
            return self.serp is not None
        if provider == "apify":
            return self.apify is not None
        if provider == "browseros":
            return self.browseros is not None
        if provider == "searchapi":
            return self.searchapi is not None
        return False

    def _provider_available(self, provider: str) -> bool:
        return provider not in self._provider_open

    @staticmethod
    def _log_discrepancies(
        keyword: str, provider_results: dict[str, int | str],
        winning_pos: int | str,
    ) -> None:
        non_match = {
            p: r for p, r in provider_results.items()
            if r != "Not Found" and r != "error" and r != winning_pos
        }
        if non_match:
            logger.warning(
                f"PROVIDER DISCREPANCY for '{keyword}': "
                f"winner says #{winning_pos}, "
                f"others say {dict(non_match)}"
            )

    # -----------------------------------------------------------------
    # Rank detection per keyword
    # -----------------------------------------------------------------
    def _search_provider(
        self, provider: str, keyword: str, location: str, device: str,
    ) -> dict[str, Any] | None:
        """Call a single provider. Returns the parsed response dict
        (shape: {"organic_results": [...]}) or None on hard error.

        Soft "not found" is signaled by an empty `organic_results` list,
        not by None. The caller distinguishes "no match" from "provider
        failed" via None.
        """
        try:
            if provider == "serpapi":
                if not self.serp:
                    return None
                data = self.serp.search(keyword, location, device)
            elif provider == "apify":
                if not self.apify:
                    return None
                data = self.apify.search(
                    keyword,
                    location=location,
                    device=device,
                    pages=APIFY_CONFIG["max_pages"],
                    results_per_page=APIFY_CONFIG["results_per_page"],
                )
            elif provider == "browseros":
                if not self.browseros:
                    return None
                data = self.browseros.search(
                    keyword, location=location, device=device, pages=3,
                )
                time.sleep(10)
            elif provider == "searchapi":
                if not self.searchapi:
                    return None
                data = self.searchapi.search(keyword, location=location)
            else:
                return None
            return data
        except Exception as e:
            kind = self._classify_error(e)
            if kind == "hard":
                self._record_hard_error(provider)
                logger.error(
                    f"Provider {provider} hard error on '{keyword}': {e}"
                )
            else:
                logger.warning(
                    f"Provider {provider} recoverable error on '{keyword}': {e}"
                )
            return None

    def _find_rank_in_organic(
        self, organic: list[dict[str, Any]], target_url: str,
    ) -> tuple[int | str, str]:
        for result in organic:
            result_url = str(result.get("link", "") or "")
            if not result_url:
                continue
            if exact_url_match(target_url, result_url):
                return result.get("position", "Not Found"), result_url
        return "Not Found", ""

    def _get_competitors(
        self, organic: list[dict[str, Any]], target_url: str,
    ) -> list[str]:
        out: list[str] = []
        for result in organic:
            url = str(result.get("link", "") or "")
            if not url:
                continue
            if not exact_url_match(target_url, url):
                out.append(url)
        return out

    def _detect_rank_for_keyword(
        self, keyword: str, target_url: str, location: str, device: str,
        apify_batch: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[int | str, str, list[str], str]:
        """Consults providers in order. Returns (position, ranking_url,
        competitors, data_availability).

        data_availability is one of: "Success (ProviderName)",
        "Not Found", or a comma-joined error summary like "serpapi=error".
        """
        last_error: str | None = None
        competitors: list[str] = []
        # Track results from each provider for discrepancy logging
        provider_results: dict[str, int | str] = {}
        # If Apify is configured to participate AND a batch result exists
        # for this keyword, prefer reusing the batch organic data.
        apify_organic: list[dict[str, Any]] | None = None
        if (
            APIFY_CONFIG["participate_in_rank_detection"]
            and self.apify
            and apify_batch is not None
        ):
            apify_item = apify_batch.get(keyword.strip().lower())
            if apify_item is not None:
                apify_organic = apify_item.get("organic_results", [])

        for provider in self.provider_order:
            if not self._provider_available(provider):
                continue

            # For Apify, reuse batch organic if we have it
            if provider == "apify" and apify_organic is not None:
                pos, rurl = self._find_rank_in_organic(apify_organic, target_url)
                provider_results[provider] = pos
                if pos != "Not Found":
                    competitors = self._get_competitors(apify_organic, target_url)
                    self._log_discrepancies(keyword, provider_results, pos)
                    return pos, rurl, competitors, f"Success ({provider_display_name(provider)})"
                # If not found in Apify batch, still try other providers
                # (Apify is participating, not the only source)
                continue

            data = self._search_provider(provider, keyword, location, device)
            if data is None:
                last_error = f"{provider}=error"
                provider_results[provider] = "error"
                continue

            organic = data.get("organic_results", [])
            pos, rurl = self._find_rank_in_organic(organic, target_url)
            provider_results[provider] = pos
            if pos != "Not Found":
                competitors = self._get_competitors(organic, target_url)
                self._log_discrepancies(keyword, provider_results, pos)
                return pos, rurl, competitors, f"Success ({provider_display_name(provider)})"

        # No provider found the target
        logger.info(f"Rank results for '{keyword}': {dict(provider_results)}")
        if last_error:
            return "Not Found", "", [], last_error
        return "Not Found", "", [], "Not Found"

    # -----------------------------------------------------------------
    # Feature value resolution (YES / NO / N/A)
    # -----------------------------------------------------------------
    def _classify_ai_overview(
        self, item: dict[str, Any] | None, target_url: str,
    ) -> str:
        if not item:
            return FEATURE_NA
        ao = item.get("ai_overview")
        if ao is None:
            return FEATURE_NA
        # Block returned — check if target is in sources
        sources = ao.get("sources", []) if isinstance(ao, dict) else []
        for src in sources:
            src_url = src.get("url", "") if isinstance(src, dict) else str(src)
            if not src_url:
                continue
            if (
                target_url.rstrip("/").lower() in src_url.lower()
                or self._same_domain(target_url, src_url)
            ):
                return FEATURE_YES
        return FEATURE_NO

    def _classify_paa(
        self, item: dict[str, Any] | None, target_url: str,
    ) -> str:
        if not item:
            return FEATURE_NA
        paa = item.get("people_also_ask")
        if not isinstance(paa, list) or not paa:
            return FEATURE_NA
        for p in paa:
            if not isinstance(p, dict):
                continue
            p_url = str(p.get("url", "") or "")
            if not p_url:
                continue
            if (
                target_url.rstrip("/").lower() in p_url.lower()
                or self._same_domain(target_url, p_url)
            ):
                return FEATURE_YES
        return FEATURE_NO

    @staticmethod
    def _same_domain(a: str, b: str) -> bool:
        try:
            return (
                urlparse(a).netloc.lower().replace("www.", "")
                == urlparse(b).netloc.lower().replace("www.", "")
            )
        except Exception:
            return False

    # -----------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------
    def run(self, keywords: list[dict[str, Any]] | None = None) -> list[list[Any]]:
        self._persist_history()

        # Reset breaker state for this run
        self._breaker = {p: 0 for p in self.provider_order}
        self._provider_open = set()

        # Use the passed keywords, then the ctor-time keywords, then
        # read from the sheet.
        records = (
            keywords
            if keywords is not None
            else (self.keywords if self.keywords is not None else None)
        )
        if records is None:
            keywords_ws = self.sheet.get_tab("Keywords")
            records = keywords_ws.get_all_records()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_label = datetime.now().strftime("%Y-%m-%d")

        # Collect valid rows (has keyword + target url + active)
        valid_rows: list[dict[str, Any]] = []
        for row in records:
            keyword = str(row.get("Keyword", "")).strip()
            target_url = str(row.get("Target URL", "")).strip()
            active = str(row.get("Active", "TRUE")).strip().upper() in (
                "TRUE", "YES", "1", ""
            )
            if not active:
                continue
            if keyword and target_url:
                valid_rows.append(row)
            if len(valid_rows) >= self.max_keywords:
                break

        # -----------------------------------------------------------------
        # ONE Apify batch call (used for both rank participation and
        # feature block harvesting).
        # -----------------------------------------------------------------
        apify_batch: dict[str, dict[str, Any]] = {}
        if self.apify and valid_rows:
            try:
                batch_kws = [
                    str(r.get("Keyword", "")).strip() for r in valid_rows
                ]
                apify_batch = self.apify.search_batch(
                    batch_kws,
                    pages=APIFY_CONFIG["max_pages"],
                    results_per_page=APIFY_CONFIG["results_per_page"],
                )
                logger.info(
                    f"Apify batch: 1 call for {len(batch_kws)} keywords "
                    f"(organic reused for rank; feature blocks harvested)"
                )
            except ApifyError as e:
                logger.warning(f"Apify batch failed: {e}")

        output: list[list[Any]] = [list(SERP_HEADERS)]
        rank_entries: list[dict[str, Any]] = []

        for row in valid_rows:
            keyword = str(row.get("Keyword", "")).strip()
            target_url = str(row.get("Target URL", "")).strip()
            location_raw = str(row.get("Location", "")).strip()
            device = str(row.get("Device", "")).strip() or "Desktop"
            search_intent = str(row.get("Search Intent", "")).strip()
            search_location = normalize_location(location_raw)

            logger.info(
                f"SERP snapshot: '{keyword}' @ '{search_location}' [{device}]"
            )

            position, ranking_url, competitors, data_avail = (
                self._detect_rank_for_keyword(
                    keyword, target_url, search_location, device,
                    apify_batch=apify_batch,
                )
            )

            apify_item = apify_batch.get(keyword.strip().lower())
            ai_overview_val = self._classify_ai_overview(apify_item, target_url)
            paa_val = self._classify_paa(apify_item, target_url)

            logger.info(
                f"SERP snapshot: '{keyword}' -> position {position} "
                f"with {len(competitors)} competitors "
                f"(AI={ai_overview_val} PAA={paa_val})"
            )

            output.append([
                keyword,
                target_url,
                search_location,
                device,
                timestamp,
                str(position),
                ranking_url,
                ai_overview_val,
                paa_val,
                data_avail,
            ])

            rank_entries.append({
                "keyword": keyword,
                "target_url": target_url,
                "location": search_location,
                "device": device,
                "search_intent": search_intent,
                "position": str(position),
                "ranking_url": ranking_url,
                "competitors": competitors,
            })

        # --- Write outputs ---
        if len(output) > 1:
            try:
                self._update_serp_snapshot(output)
                logger.info(f"SERP Snapshot: wrote {len(output) - 1} rows")
            except Exception as e:
                logger.warning(f"Could not write SERP Snapshot: {e}")

            try:
                self._update_serp_tab(rank_entries, date_label)
            except (SerpTabSchemaError, DuplicateDateColumnError) as e:
                logger.critical(f"SERP tab update aborted: {e}")
            except Exception as e:
                logger.warning(f"Could not update SERP tab: {e}")
        else:
            logger.warning("SERP Snapshot: no valid rows to write")

        if rank_entries:
            try:
                self._update_competitor_snapshot(rank_entries)
            except Exception as e:
                logger.error(f"Competitor Snapshot write FAILED: {e}", exc_info=True)
                raise

        return output

    def _update_serp_snapshot(self, output: list[list[Any]]) -> None:
        """In-place match on Keyword + Target URL.

        Existing rows are updated for that keyword+url. New keywords are
        appended. The header row is preserved.
        """
        try:
            ws = self.sheet.get_or_create_tab(SERP_SNAPSHOT_TAB, rows=200, cols=20)
            existing = ws.get_all_values()

            new_header = output[0]
            new_data_rows = output[1:]

            if not existing or len(existing) < 1:
                # First run — write header + data
                ws.update(range_name="A1", values=output)
                return

            # Ensure the existing header matches; if not, fix it.
            existing_header = existing[0]
            if existing_header[:len(new_header)] != new_header:
                # Different schema — rewrite whole tab
                ws.clear()
                ws.update(range_name="A1", values=output)
                return

            # Index existing rows by (keyword, target_url) -> row number
            existing_index: dict[tuple[str, str], int] = {}
            for i, row in enumerate(existing[1:], start=2):
                if len(row) < 2:
                    continue
                kw = (row[0] or "").strip().lower()
                url = (row[1] or "").strip().lower()
                if kw and url:
                    existing_index[(kw, url)] = i

            # Update existing rows, append new ones
            new_appends: list[list[Any]] = []
            for new_row in new_data_rows:
                key = (
                    new_row[0].strip().lower(),
                    new_row[1].strip().lower(),
                )
                if key in existing_index:
                    row_num = existing_index[key]
                    end_col = self._col_letter(len(new_row))
                    ws.update(
                        range_name=f"A{row_num}:{end_col}{row_num}",
                        values=[new_row],
                    )
                else:
                    new_appends.append(new_row)

            if new_appends:
                ws.append_rows(values=new_appends, value_input_option="USER_ENTERED")
                logger.info(
                    f"SERP Snapshot: appended {len(new_appends)} new rows"
                )
        except Exception as e:
            logger.warning(f"Could not update SERP Snapshot: {e}")
            raise
