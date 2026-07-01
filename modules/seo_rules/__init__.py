"""SEO Rules Engine — 269 CrawlForge-derived rules adapted for our pipeline.

All data stays local (DuckDB in-memory). No third-party calls.
"""

from modules.seo_rules._runner import run_seo_rules

__all__ = ["run_seo_rules"]
