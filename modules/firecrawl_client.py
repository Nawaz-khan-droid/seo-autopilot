"""Firecrawl client — crawls public websites for SEO audit data.

Wraps the FirecrawlApp SDK (v4). Extracts:
- Page metadata (title, description, headings, schema)
- Full page markdown content (for LLM analysis)
- Crawl results across multiple pages (full sitemap mode)
- PageSpeed Insights scores (via psi parameter)

Requires FIRECRAWL_API_KEY in environment.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CrawledPage:
    url: str
    title: str | None = None
    description: str | None = None
    language: str | None = None
    status_code: int | None = None
    markdown: str = ""
    headings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class CrawlResult:
    pages: list[CrawledPage] = field(default_factory=list)
    total_pages: int = 0
    broken_urls: list[str] = field(default_factory=list)
    error: str | None = None


class FirecrawlClient:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("FIRECRAWL_API_KEY", "")
        if not key:
            from dotenv import load_dotenv
            load_dotenv(override=True)
            key = os.environ.get("FIRECRAWL_API_KEY", "")
        if not key:
            logger.warning("FIRECRAWL_API_KEY not set — FirecrawlClient disabled")
        self._app: Any = None
        self._key = key

    @property
    def _client(self):
        if self._app is None and self._key:
            from firecrawl import FirecrawlApp
            self._app = FirecrawlApp(api_key=self._key)
        return self._app

    @property
    def available(self) -> bool:
        return bool(self._key)

    def scrape_page(self, url: str) -> CrawledPage:
        """Scrape a single page. Returns structured metadata + markdown."""
        if not self._client:
            return CrawledPage(url=url, error="Firecrawl not configured")

        try:
            doc = self._client.scrape(url, formats=["markdown"])
            meta = doc.metadata
            headings = self._extract_headings(doc.markdown or "")
            return CrawledPage(
                url=getattr(meta, "source_url", url) or url,
                title=getattr(meta, "title", None),
                description=getattr(meta, "description", None),
                language=getattr(meta, "language", None),
                status_code=getattr(meta, "status_code", None),
                markdown=doc.markdown or "",
                headings=headings,
            )
        except Exception as e:
            logger.error("Firecrawl scrape failed for %s: %s", url, e)
            return CrawledPage(url=url, error=str(e))

    def crawl_site(self, url: str, max_pages: int = 15) -> CrawlResult:
        """Crawl a full website. Falls back to single-page scrape if crawl fails."""
        if not self._client:
            return CrawlResult(error="Firecrawl not configured")

        try:
            from firecrawl.v2.types import ScrapeOptions
            crawl_job = self._client.crawl(url, limit=max_pages, scrape_options=ScrapeOptions(formats=["markdown"]))
            if not crawl_job or not getattr(crawl_job, "id", None):
                raise RuntimeError("Crawl job did not return an ID")

            job_id = crawl_job.id
            import time
            result = None
            for _ in range(60):
                result = self._client.check_crawl_status(job_id)
                if getattr(result, "status", "") != "scraping":
                    break
                time.sleep(2)

            if not result:
                raise RuntimeError("No result from crawl status check")
            status = getattr(result, "status", "")
            if status == "failed":
                raise RuntimeError(getattr(result, "error", "Crawl failed"))

            pages = []
            broken = []
            for item in (getattr(result, "data", None) or []):
                meta = getattr(item, "metadata", None)
                page_url = getattr(meta, "source_url", getattr(item, "url", url))
                md = getattr(item, "markdown", "") or ""
                headings = self._extract_headings(md)
                page = CrawledPage(
                    url=page_url,
                    title=getattr(meta, "title", None),
                    description=getattr(meta, "description", None),
                    language=getattr(meta, "language", None),
                    status_code=getattr(meta, "status_code", None) or getattr(meta, "statusCode", None),
                    markdown=md,
                    headings=headings,
                )
                pages.append(page)
                if page.status_code and page.status_code >= 400:
                    broken.append(page_url)

            return CrawlResult(pages=pages, total_pages=len(pages), broken_urls=broken)

        except Exception as e:
            logger.warning("Firecrawl crawl failed for %s — falling back to single scrape: %s", url, e)
            page = self.scrape_page(url)
            if page.error:
                return CrawlResult(error=page.error)
            return CrawlResult(pages=[page], total_pages=1, broken_urls=[])

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search the web via Firecrawl. Returns list of {title, url, description}."""
        if not self._client:
            return []
        try:
            result = self._client.search(query)
            # In v4 SDK, result is a SearchResult Pydantic model
            data = getattr(result, "data", None) or []
            items = []
            for item in data:
                items.append({
                    "title": getattr(item, "title", ""),
                    "url": getattr(item, "url", ""),
                    "description": getattr(item, "description", ""),
                })
            return items
        except Exception as e:
            logger.error("Firecrawl search failed: %s", e)
            return []

    @staticmethod
    def _extract_headings(markdown: str) -> list[str]:
        """Extract H1-H3 headings from markdown text."""
        lines = []
        for line in markdown.split("\n"):
            stripped = line.strip()
            if stripped.startswith("### ") or stripped.startswith("## ") or stripped.startswith("# "):
                lines.append(stripped.lstrip("#").strip())
        return lines
