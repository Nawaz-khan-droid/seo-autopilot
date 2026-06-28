from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.browseros_client import BrowserOSClient
from modules.groq_client import GroqClient
from modules.sheet_client import SheetClient

logger = logging.getLogger(__name__)

PLAN_HEADERS = [
    "Date",
    "Section",
    "Item",
    "Details",
    "Priority",
]

MONTHLY_PLAN_TAB = "Monthly SEO Plan"

SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "config" / "prompts" / "monthly_seo_plan_prompt.txt"
)


class MonthlySeoPlanWorkflow:
    def __init__(
        self,
        sheet: SheetClient,
        groq: GroqClient,
        browseros: BrowserOSClient | None = None,
    ) -> None:
        self.sheet = sheet
        self.groq = groq
        self.browseros = browseros
        self._system_prompt = self._load_prompt()

    @staticmethod
    def _load_prompt() -> str | None:
        try:
            return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning(f"Could not load monthly plan prompt: {e}")
            return None

    def _read_tab(self, tab_name: str) -> list[dict[str, Any]]:
        try:
            ws = self.sheet.get_tab(tab_name)
            return ws.get_all_records()
        except Exception as e:
            logger.debug(f"Could not read tab '{tab_name}': {e}")
            return []

    def _build_context(self) -> str:
        sections: list[str] = []

        # Current rankings from SERP Snapshot
        snapshot = self._read_tab("SERP Snapshot")
        if snapshot:
            lines = ["CURRENT RANKINGS (SERP Snapshot):"]
            for row in snapshot:
                kw = row.get("Keyword", "")
                pos = row.get("Position", "N/A")
                url = row.get("Ranking URL", "")
                ai = row.get("AI Overview Mention", "N/A")
                paa = row.get("PAA Mention", "N/A")
                lines.append(f"  - {kw}: pos={pos} url={url} ai_overview={ai} paa={paa}")
            sections.append("\n".join(lines))

        # Historical trends from SERP History
        history = self._read_tab("SERP History")
        if history:
            lines = ["HISTORICAL TRENDS (SERP History):"]
            kw_trends: dict[str, list[str]] = {}
            for row in history:
                kw = str(row.get("Keyword", "") or "").strip()
                pos = str(row.get("Position", "") or "").strip()
                ts = str(row.get("Timestamp", "") or "").strip()
                if kw and pos:
                    kw_trends.setdefault(kw, []).append(f"{ts}={pos}")
            for kw, entries in sorted(kw_trends.items()):
                lines.append(f"  - {kw}: {', '.join(entries[-10:])}")
            sections.append("\n".join(lines))

        # Website Insights
        insights = self._read_tab("Website Tracking & Insights")
        if insights:
            lines = ["WEBSITE INSIGHTS:"]
            for row in insights:
                url = row.get("URL", "")
                mobile = row.get("Mobile PSI", "N/A")
                desktop = row.get("Desktop PSI", "N/A")
                clicks = row.get("Clicks", "N/A")
                impressions = row.get("Impressions", "N/A")
                lines.append(
                    f"  - {url}: mobile_psi={mobile} desktop_psi={desktop} "
                    f"clicks={clicks} impressions={impressions}"
                )
            sections.append("\n".join(lines))

        # AI Analysis summaries
        ai_analysis = self._read_tab("AI Analysis")
        if ai_analysis:
            lines = ["PREVIOUS AI ANALYSIS:"]
            for row in ai_analysis[-20:]:
                kw = row.get("Keyword", "")
                change = row.get("Observed Change", "")
                cause = row.get("Likely Cause", "")
                rec = row.get("Recommendation", "")
                priority = row.get("Priority", "")
                lines.append(
                    f"  - {kw}: change={change[:100]} cause={cause[:100]} "
                    f"rec={rec[:100]} priority={priority}"
                )
            sections.append("\n".join(lines))

        return "\n\n".join(sections) if sections else "No data available."

    def run(self) -> list[list[Any]]:
        logger.info("Monthly SEO Plan: building context...")
        context = self._build_context()

        # Site audit via BrowserOS (from target URLs in SERP Snapshot)
        audit_data: list[dict[str, Any]] = []
        if self.browseros:
            snapshot = self._read_tab("SERP Snapshot")
            target_urls: list[str] = []
            seen: set[str] = set()
            for row in snapshot:
                url = str(row.get("Target URL", "") or "").strip()
                if url and url not in seen:
                    seen.add(url)
                    target_urls.append(url)
            for url in target_urls:
                logger.info(f"Monthly SEO Plan: auditing {url} via BrowserOS...")
                try:
                    audit = self.browseros.audit_page(url)
                    audit_data.append(audit)
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"BrowserOS audit failed for {url}: {e}")

        if audit_data:
            lines = ["SITE AUDIT (BrowserOS):"]
            for a in audit_data:
                issues = "; ".join(a.get("issues", []))
                lines.append(
                    f"  - {a.get('url', '')}: title={a.get('title','')[:60]} "
                    f"h1={a.get('h1','')[:60]} word_count={a.get('wordCount','')} "
                    f"issues=[{issues}]"
                )
            context += "\n\n" + "\n".join(lines)

        if not self._system_prompt:
            logger.error("Monthly SEO Plan: no system prompt — aborting")
            return []

        logger.info(f"Monthly SEO Plan: sending to Groq ({len(context)} chars)...")

        try:
            result = self.groq.chat(
                prompt=context,
                system_prompt=self._system_prompt,
                max_tokens=2000,
            )
            if not result:
                logger.warning("Monthly SEO Plan: Groq returned empty result")
                return []
        except Exception as e:
            logger.error(f"Monthly SEO Plan: Groq call failed — {e}")
            return []

        today = datetime.now().strftime("%Y-%m-%d")
        lines = result.strip().split("\n")
        output: list[list[Any]] = [list(PLAN_HEADERS)]
        current_section = "General"

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.upper().startswith(("CRITICAL ACTIONS", "KEYWORD PRIORITIES",
                                            "TECHNICAL FIXES", "CONTENT GAPS",
                                            "TIMELINE")):
                current_section = stripped
                output.append([today, current_section, "", "", ""])
            else:
                is_item = stripped.startswith("-") or stripped.startswith("|")
                item_text = stripped.lstrip("-| ").strip()
                priority = ""
                if "high" in stripped.lower():
                    priority = "High"
                elif "medium" in stripped.lower():
                    priority = "Medium"
                elif "low" in stripped.lower():
                    priority = "Low"
                if current_section == "KEYWORD PRIORITIES" and stripped.startswith("|"):
                    parts = [p.strip() for p in stripped.strip("|").split("|")]
                    if len(parts) >= 3:
                        output.append([
                            today, current_section, parts[0],
                            " | ".join(parts[1:]),
                            parts[-1] if parts[-1] in ("High", "Medium", "Low") else "",
                        ])
                    else:
                        output.append([today, current_section, item_text, "", priority])
                else:
                    output.append([today, current_section, item_text, "", priority])

        # Write to sheet
        if len(output) > 1:
            try:
                self._write_plan(output)
                logger.info(f"Monthly SEO Plan: wrote {len(output) - 1} items")
            except Exception as e:
                logger.error(f"Monthly SEO Plan write failed: {e}")

        return output

    def _write_plan(self, rows: list[list[Any]]) -> None:
        ws = self.sheet.get_or_create_tab(MONTHLY_PLAN_TAB, rows=200, cols=10)
        existing = ws.get_all_values()
        if existing:
            ws.clear()
        ws.update(range_name="A1", values=rows)
