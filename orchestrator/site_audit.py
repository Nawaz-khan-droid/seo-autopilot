from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from modules.browseros_client import BrowserOSClient
from modules.groq_client import GroqClient
from modules.sheet_client import SheetClient

logger = logging.getLogger(__name__)

AUDIT_TAB = "Site Audit"
AUDIT_HEADERS = [
    "Date",
    "URL",
    "Title",
    "H1",
    "Word Count",
    "Issues",
    "Internal Links",
    "External Links",
    "Images",
    "Images Missing Alt",
    "Has HTTPS",
    "Has Canonical",
    "LLM Summary",
]

SITE_AUDIT_SYSTEM_PROMPT = """You are a technical SEO auditor. Given the crawl data for a website page, summarize the key technical issues and their SEO impact. Focus on:

1. Critical issues (missing title, missing h1, no HTTPS, broken structure)
2. Content quality (thin content, keyword relevance)
3. On-page optimization (headings hierarchy, image alt text, meta description)
4. Actionable fixes

Be concise. Output exactly two sections:
Issues Summary: <2-3 sentences>
Top Fix: <1 specific action>
"""


class SiteAuditWorkflow:
    def __init__(
        self,
        sheet: SheetClient,
        groq: GroqClient,
        browseros: BrowserOSClient | None = None,
    ) -> None:
        self.sheet = sheet
        self.groq = groq
        self.browseros = browseros

    def run(self, keywords: list[dict[str, Any]] | None = None) -> list[list[Any]]:
        if not self.browseros:
            logger.info("Site Audit: no BrowserOS client — skipping")
            return []

        # Collect unique target URLs
        target_urls: list[str] = []
        seen: set[str] = set()
        if keywords:
            for row in keywords:
                url = str(row.get("Target URL", "") or "").strip()
                if url and url not in seen:
                    seen.add(url)
                    target_urls.append(url)

        if not target_urls:
            logger.info("Site Audit: no target URLs — skipping")
            return []

        today = datetime.now().strftime("%Y-%m-%d")
        output: list[list[Any]] = [list(AUDIT_HEADERS)]

        for url in target_urls:
            logger.info(f"Site Audit: crawling {url}...")
            try:
                # Crawl up to 5 pages from this start URL
                pages = self.browseros.crawl_site(url, max_pages=5)
            except Exception as e:
                logger.warning(f"Site Audit: crawl failed for {url}: {e}")
                continue

            for page in pages:
                issues_list = page.get("issues", [])
                issues_str = "; ".join(issues_list[:10]) if issues_list else "None"
                llm_summary = self._llm_summarize(page)

                output.append([
                    today,
                    page.get("url", url),
                    (page.get("title", "") or "")[:80],
                    (page.get("h1", "") or "")[:80],
                    page.get("wordCount", 0),
                    issues_str,
                    page.get("internalLinks", 0),
                    page.get("externalLinks", 0),
                    page.get("totalImages", 0),
                    page.get("imagesWithoutAlt", 0),
                    "Yes" if page.get("isHTTPS", True) else "No",
                    "Yes" if page.get("canonical") else "No",
                    llm_summary,
                ])

            time.sleep(1)

        if len(output) > 1:
            try:
                self._write_audit(output)
                logger.info(f"Site Audit: wrote {len(output) - 1} page audits")
            except Exception as e:
                logger.error(f"Site Audit write failed: {e}")

        return output

    def _llm_summarize(self, page: dict[str, Any]) -> str:
        issues = page.get("issues", [])
        prompt_lines = [
            f"URL: {page.get('url', '')}",
            f"Title: {page.get('title', 'N/A')}",
            f"H1: {page.get('h1', 'N/A')}",
            f"Word Count: {page.get('wordCount', 0)}",
            f"Issues: {'; '.join(issues[:10]) if issues else 'None found'}",
            f"Images: {page.get('totalImages', 0)} ({page.get('imagesWithoutAlt', 0)} missing alt)",
            f"HTTPS: {page.get('isHTTPS', True)}",
            f"Canonical: {page.get('canonical', 'N/A')}",
        ]
        prompt = "\n".join(prompt_lines)

        try:
            result = self.groq.chat(
                prompt=prompt,
                system_prompt=SITE_AUDIT_SYSTEM_PROMPT,
                max_tokens=500,
            )
            return (result or "N/A")[:300]
        except Exception as e:
            logger.debug(f"Site Audit LLM summary failed: {e}")
            return "N/A"

    def _write_audit(self, rows: list[list[Any]]) -> None:
        ws = self.sheet.get_or_create_tab(AUDIT_TAB, rows=200, cols=20)
        existing = ws.get_all_values()
        if existing:
            ws.clear()
        ws.update(range_name="A1", values=rows)
