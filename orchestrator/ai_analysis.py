from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.groq_client import GroqClient
from modules.openrouter_client import OpenRouterClient
from modules.sheet_client import SheetClient

logger = logging.getLogger(__name__)

# Approved schema: 6 columns, append-only.
# Date is the first column (when this row was analyzed).
# Local Maps and Paid Ads are NOT included — probe confirmed the
# Apify actor does not return them. AI Overview Mention and PAA
# Mention are read from SERP Snapshot as YES/NO/N/A strings.
AI_HEADERS = [
    "Date",
    "Keyword",
    "Observed Change",
    "Likely Cause",
    "Recommendation",
    "Priority",
]

SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "config" / "prompts" / "seo_analysis_system_prompt.txt"
)
OLD_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "config" / "prompts" / "llm_system_prompt.txt"
)

USER_PROMPT_TEMPLATE = (
    "Analyze this keyword's SEO performance using the provided data.\n\n"
    "--- Row Data ---\n"
    "Keyword: {keyword}\n"
    "Target URL: {target_url}\n"
    "Search Location: {location}\n"
    "Device: {device}\n"
    "Search Intent: {search_intent}\n"
    "Current Position: {position}\n"
    "Ranking URL: {ranking_url}\n"
    "Top Competitors: {competitors}\n"
    "AI Overview Mention: {ai_overview_mention}\n"
    "PAA Mention: {paa_mention}\n\n"
    "--- Historical Context ---\n"
    "{historical_context}\n\n"
    "--- Website Metrics ---\n"
    "PageSpeed Mobile: {mobile_speed}\n"
    "PageSpeed Desktop: {desktop_speed}\n"
    "Clicks: {clicks}\n"
    "Impressions: {impressions}\n\n"
    "--- Site Audit Issues ---\n"
    "{site_audit_issues}\n"
)


def _load_system_prompt(path: Path | None = None) -> str | None:
    if path is None:
        path = SYSTEM_PROMPT_PATH
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        try:
            return OLD_PROMPT_PATH.read_text(encoding="utf-8").strip()
        except Exception:
            logger.warning("Could not load any system prompt file")
            return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        logger.warning(f"Could not load system prompt from {path}")
        return None


def _classify_search_intent_rule(keyword: str, target_url: str) -> str:
    """Rule-based search intent classification."""
    kw_lower = keyword.lower()
    url_lower = target_url.lower()

    cities = ["mumbai", "delhi", "bangalore", "pune", "hyderabad",
              "chennai", "kolkata", "ahmedabad", "india"]
    service_terms = ["agency", "services", "company", "experts",
                     "consultant", "consulting", "provider"]
    has_city = any(c in kw_lower for c in cities)
    has_service = any(s in kw_lower for s in service_terms)
    if has_city and has_service:
        return "Local Commercial"

    transactional_terms = ["buy", "hire", "price", "pricing", "cost",
                           "purchase", "order", "consultation", "quote",
                           "contact", "book", "sign up", "register"]
    if any(t in kw_lower for t in transactional_terms):
        return "Transactional"

    navigational_terms = ["login", "sign in", "website", "homepage",
                          "official", "linkedin", "twitter", "facebook"]
    if any(n in kw_lower for n in navigational_terms):
        return "Navigational"

    informational_terms = ["how to", "what is", "why is", "guide",
                           "tutorial", "tips", "best way", "example",
                           "definition", "meaning", "vs", "or"]
    if any(t in kw_lower for t in informational_terms):
        return "Informational"

    commercial_terms = ["best", "top", "review", "compare", "vs",
                        "rating", "recommended", "affordable"]
    if any(t in kw_lower for t in commercial_terms) or has_service:
        return "Commercial"

    return "Mixed"


class AiAnalysisWorkflow:
    def __init__(
        self,
        sheet: SheetClient,
        groq: GroqClient,
        openrouter: OpenRouterClient | None = None,
        keywords: list[dict[str, Any]] | None = None,
    ) -> None:
        self.sheet = sheet
        self.groq = groq
        self.openrouter = openrouter
        self.keywords = keywords  # optional pre-loaded keywords
        self._system_prompt = _load_system_prompt()

    def _load_search_intent(self) -> dict[str, str]:
        """Read Search Intent from Keywords tab."""
        try:
            ws = self.sheet.get_tab("Keywords")
            records = ws.get_all_records()
            intent_map: dict[str, str] = {}
            for rec in records:
                kw = str(rec.get("Keyword", "") or "").strip().lower()
                intent = str(rec.get("Search Intent", "") or "").strip()
                if kw and intent:
                    intent_map[kw] = intent
            return intent_map
        except Exception:
            return {}

    def _load_insights_by_url(
        self,
    ) -> dict[str, dict[str, str]]:
        try:
            ws = self.sheet.get_tab("Website Tracking & Insights")
            records = ws.get_all_records()
            lookup: dict[str, dict[str, str]] = {}
            for rec in records:
                url = str(rec.get("URL", "") or "").strip().lower()
                if url:
                    lookup[url] = {
                        "mobile_speed": str(rec.get("Mobile PSI", "N/A") or "N/A"),
                        "desktop_speed": str(rec.get("Desktop PSI", "N/A") or "N/A"),
                        "clicks": str(rec.get("Clicks", "N/A") or "N/A"),
                        "impressions": str(rec.get("Impressions", "N/A") or "N/A"),
                    }
            return lookup
        except Exception:
            return {}

    def _load_history_by_keyword(
        self,
    ) -> dict[str, str]:
        try:
            ws = self.sheet.get_tab("SERP History")
            records = ws.get_all_records()
            history_raw: dict[str, list[tuple[str, str]]] = {}
            for rec in records:
                kw = str(rec.get("Keyword", "") or "").strip().lower()
                pos = str(rec.get("Position", "") or "").strip()
                ts = str(rec.get("Run Date", "") or "").strip()
                if not ts:
                    ts = str(rec.get("Timestamp", "") or "").strip()
                if kw and pos and pos not in ("Not Found", "Error", ""):
                    history_raw.setdefault(kw, []).append((ts, pos))
            history: dict[str, str] = {}
            for kw, entries in history_raw.items():
                entries.sort(key=lambda x: x[0])
                recent = entries[-5:]
                trend = ", ".join(f"{t[:10]}={p}" for t, p in recent)
                last_pos = recent[-1][1] if recent else "N/A"
                history[kw] = f"{last_pos}|trend:{trend}"
            return history
        except Exception:
            return {}

    def _load_audit_by_url(self) -> dict[str, str]:
        try:
            ws = self.sheet.get_tab("Site Audit")
            records = ws.get_all_records()
            raw: dict[str, list[str]] = {}
            for rec in records:
                url = str(rec.get("URL", "") or "").strip().lower()
                issues = str(rec.get("Issues", "") or "").strip()
                if url and issues and issues != "None":
                    raw.setdefault(url, []).append(issues)
            return {url: "; ".join(iss[:3]) for url, iss in raw.items()}
        except Exception:
            return {}

    def run(self, keywords: list[dict[str, Any]] | None = None) -> list[list[Any]]:
        snapshot_ws = self.sheet.get_tab("SERP Snapshot")
        records = snapshot_ws.get_all_records()
        insights_lookup = self._load_insights_by_url()
        audit_lookup = self._load_audit_by_url()
        history_lookup = self._load_history_by_keyword()
        intent_lookup = self._load_search_intent()

        today = datetime.now().strftime("%Y-%m-%d")
        output: list[list[Any]] = [list(AI_HEADERS)]

        for row in records:
            keyword = str(row.get("Keyword", "") or "").strip()
            target_url = str(row.get("Target URL", "") or "").strip()
            location = str(row.get("Search Location", "") or "").strip()
            device = str(row.get("Device", "") or "Desktop").strip()
            position = str(row.get("Position", "") or "N/A").strip()
            ranking_url = str(row.get("Ranking URL", "") or "").strip()
            ai_overview_mention = str(
                row.get("AI Overview Mention", "N/A") or "N/A"
            ).strip()
            paa_mention = str(
                row.get("PAA Mention", "N/A") or "N/A"
            ).strip()

            if not keyword or not target_url:
                continue

            url_key = target_url.strip().lower()
            insight = insights_lookup.get(url_key, {})
            mobile_speed = insight.get("mobile_speed", "N/A")
            desktop_speed = insight.get("desktop_speed", "N/A")
            clicks_data = insight.get("clicks", "N/A")
            impressions_data = insight.get("impressions", "N/A")

            kw_key = keyword.strip().lower()
            search_intent = intent_lookup.get(
                kw_key,
                _classify_search_intent_rule(keyword, target_url),
            )

            history_entry = history_lookup.get(kw_key)
            if history_entry:
                parts = history_entry.split("|")
                prev_position = parts[0]
                trend = parts[1].replace("trend:", "") if len(parts) > 1 else ""
                delta = self._compute_delta(prev_position, position)
                historical_context = (
                    f"Previous position: {prev_position}\n"
                    f"Current position: {position}\n"
                    f"Delta: {delta}\n"
                    f"Recent trend: {trend}"
                )
            else:
                prev_position = None
                historical_context = "Historical context unavailable."

            competitors_list: list[str] = []
            for ckey in ["Top Competitor 1 URL", "Top Competitor 2 URL", "Top Competitor 3 URL"]:
                val = str(row.get(ckey, "") or "").strip()
                if val:
                    competitors_list.append(val)
            competitors_str = (
                ", ".join(competitors_list) if competitors_list else "None provided"
            )

            site_audit_issues = audit_lookup.get(url_key, "No audit data available")

            prompt = USER_PROMPT_TEMPLATE.format(
                keyword=keyword,
                target_url=target_url,
                location=location,
                device=device,
                search_intent=search_intent,
                position=position,
                ranking_url=ranking_url,
                competitors=competitors_str,
                ai_overview_mention=ai_overview_mention,
                paa_mention=paa_mention,
                historical_context=historical_context,
                mobile_speed=mobile_speed,
                desktop_speed=desktop_speed,
                clicks=clicks_data,
                impressions=impressions_data,
                site_audit_issues=site_audit_issues,
            )

            try:
                result = self.groq.chat(
                    prompt=prompt,
                    system_prompt=self._system_prompt,
                )

                if not result and self.openrouter:
                    logger.info(
                        f"Groq returned no result, trying OpenRouter for '{keyword}'"
                    )
                    result = self.openrouter.chat(
                        prompt=prompt,
                        system_prompt=self._system_prompt,
                    )

                if result:
                    parsed = self._parse_analysis(result)
                    logger.info(
                        f"AI parsed for '{keyword}': "
                        f"change='{parsed['change'][:80]}' "
                        f"cause='{parsed['cause'][:80]}' "
                        f"priority={parsed['priority']}"
                    )
                else:
                    logger.warning(
                        f"AI LLM returned no result for '{keyword}' — "
                        f"using fallback analysis"
                    )
                    parsed = self._fallback_analysis(position, prev_position, search_intent)
                    logger.info(
                        f"AI fallback for '{keyword}': "
                        f"change='{parsed['change'][:80]}' "
                        f"cause='{parsed['cause'][:80]}'"
                    )

                output.append([
                    today,
                    keyword,
                    parsed["change"],
                    parsed["cause"],
                    parsed["recommendation"],
                    parsed["priority"],
                ])
                logger.info(f"AI analysis done for '{keyword}'")
            except Exception as e:
                logger.error(
                    f"AI analysis failed for '{keyword}': {e}", exc_info=True
                )
                output.append([
                    today,
                    keyword,
                    f"Position {position}",
                    "Analysis unavailable",
                    "Manual review recommended",
                    "Medium",
                ])

        if len(output) > 1:
            logger.info(
                f"AI Analysis: output list has {len(output) - 1} data rows; "
                f"writing now"
            )
            for idx, out_row in enumerate(output[1:], 1):
                logger.info(
                    f"  output[{idx}]: date='{out_row[0]}' "
                    f"keyword='{out_row[1]}' change_len={len(out_row[2] or '')} "
                    f"cause_len={len(out_row[3] or '')} "
                    f"rec_len={len(out_row[4] or '')} "
                    f"priority='{out_row[5]}'"
                )
            try:
                self._write_append_only("AI Analysis", output, dedup_on=("Date", "Keyword"))
                logger.info(f"AI Analysis: wrote {len(output) - 1} rows")
                try:
                    verify_ws = self.sheet.get_tab("AI Analysis")
                    verify_rows = verify_ws.get_all_values()
                    logger.info(
                        f"AI Analysis verify: tab now has {len(verify_rows)} rows; "
                        f"last 4: {[r[1] if len(r) > 1 else '<empty>' for r in verify_rows[-4:]]}"
                    )
                except Exception as ve:
                    logger.warning(f"AI Analysis verify failed: {ve}")
            except Exception as e:
                logger.error(f"AI Analysis row write FAILED: {e}", exc_info=True)
                raise

        return output

    def _write_append_only(
        self, tab_name: str, new_rows: list[list[Any]],
        dedup_on: tuple[str, str] = ("Date", "Keyword"),
    ) -> None:
        """Append new rows to AI Analysis tab. If a (date, keyword) pair
        already exists, the previous row is removed first to keep the
        tab dedup-safe when re-running the same day.
        """
        try:
            ws = self.sheet.get_or_create_tab(tab_name, rows=500, cols=10)
            existing = ws.get_all_values()

            if not existing or len(existing) < 1:
                ws.update(range_name="A1", values=new_rows)
                return

            header = existing[0]
            if header[:len(new_rows[0])] != new_rows[0]:
                ws.clear()
                ws.update(range_name="A1", values=new_rows)
                return

            try:
                date_col = header.index(dedup_on[0])
                kw_col = header.index(dedup_on[1])
            except ValueError:
                date_col, kw_col = 0, 1

            new_data = new_rows[1:]
            rows_to_delete: list[int] = []
            for i, row in enumerate(existing[1:], start=2):
                if len(row) <= max(date_col, kw_col):
                    continue
                row_date = (row[date_col] or "").strip()
                row_kw = (row[kw_col] or "").strip().lower()
                for new_row in new_data:
                    new_date = (str(new_row[date_col]) or "").strip()
                    new_kw = (str(new_row[kw_col]) or "").strip().lower()
                    if row_date == new_date and row_kw == new_kw:
                        rows_to_delete.append(i)
                        break

            for row_num in sorted(rows_to_delete, reverse=True):
                ws.delete_rows(row_num)

            logger.info(
                f"AI Analysis _write_append_only: {len(rows_to_delete)} rows deleted, "
                f"{len(new_data)} new rows about to be appended"
            )
            for idx, new_row in enumerate(new_data, 1):
                logger.info(
                    f"  new_data[{idx}]: date='{new_row[0]}' "
                    f"keyword='{new_row[1]}' change_len={len(new_row[2] or '')} "
                    f"cause_len={len(new_row[3] or '')} "
                    f"rec_len={len(new_row[4] or '')} "
                    f"priority='{new_row[5]}'"
                )
            ws.append_rows(values=new_data, value_input_option="USER_ENTERED")
        except Exception as e:
            logger.warning(f"Could not write to '{tab_name}': {e}")
            raise

    @staticmethod
    def _compute_delta(prev: str, cur: str) -> str:
        try:
            p, c = int(prev), int(cur)
            diff = p - c
            if diff > 0:
                return f"Improved by {diff} position{'s' if diff != 1 else ''}"
            if diff < 0:
                return f"Dropped by {abs(diff)} position{'s' if diff != -1 else ''}"
            return "No change"
        except (ValueError, TypeError):
            return "Unable to compute"

    @staticmethod
    def _parse_analysis(text: str) -> dict[str, str]:
        lines = text.strip().split("\n")
        result: dict[str, str] = {
            "change": "No change detected",
            "cause": "Unable to determine",
            "recommendation": "Review content relevance and on-page SEO factors",
            "priority": "Medium",
        }

        for line in lines:
            line_lower = line.strip().lower()
            if line_lower.startswith("observed change:") or line_lower.startswith("change:"):
                _, val = line.split(":", 1)
                result["change"] = val.strip()
            elif line_lower.startswith("likely cause:") or line_lower.startswith("cause:"):
                _, val = line.split(":", 1)
                result["cause"] = val.strip()
            elif line_lower.startswith("recommendation:"):
                _, val = line.split(":", 1)
                result["recommendation"] = val.strip()
            elif line_lower.startswith("priority:"):
                _, val = line.split(":", 1)
                priority = val.strip().capitalize()
                if priority in ("High", "Medium", "Low"):
                    result["priority"] = priority
                else:
                    result["priority"] = "Medium"

        return result

    @staticmethod
    def _fallback_analysis(
        position: str,
        prev_position: str | None = None,
        search_intent: str = "",
    ) -> dict[str, str]:
        if prev_position:
            delta = AiAnalysisWorkflow._compute_delta(prev_position, position)
            change = f"Position {position} (previously {prev_position}). {delta}."
        else:
            change = (
                f"Position {position}"
                if position != "Not Found"
                else "Not found in top results"
            )

        cause = "Groq API call failed — manual check required"

        return {
            "change": change,
            "cause": cause,
            "recommendation": (
                "Review page content relevance, meta tags, "
                "and manual SEO assessment"
            ),
            "priority": "Medium",
        }
