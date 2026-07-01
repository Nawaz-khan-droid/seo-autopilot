"""Run the 269 CrawlForge-derived SEO rules against DuckDB populated with our crawl data."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import duckdb

from modules.seo_rules.storage.schema import init_database
from modules.seo_rules._populate import populate_from_crawl
from modules.seo_rules.rules._issue import Issue
from modules.seo_rules.rules._registry import discover_rules

logger = logging.getLogger(__name__)


def run_seo_rules(
    target_url: str,
    crawl_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Populate DuckDB with crawl data, run all 269 rules, return issues as dicts.

    Args:
        target_url: The audited URL.
        crawl_data: Raw dict from ``_run_playwright_headless`` or similar.
            Must contain at minimum: ``title``, ``h1_texts``, ``meta_description``,
            ``word_count``, ``link_details``, ``image_details``, etc.

    Returns:
        List of issue dicts with keys:
        ``rule_id``, ``severity``, ``category``, ``message``, ``url``, ``evidence``.
    """
    con: duckdb.DuckDBPyConnection | None = None
    all_issues: list[dict[str, Any]] = []

    try:
        con = init_database(path=None)
        populate_from_crawl(con, target_url, crawl_data)
        logger.info("DuckDB populated for %s", target_url)

        rules = discover_rules()
        enabled = {
            rid: cls for rid, cls in rules.items()
            if cls.enabled_by_default
        }
        logger.info("Running %d enabled rules (of %d total)", len(enabled), len(rules))

        for rule_id, rule_cls in enabled.items():
            try:
                rule_instance = rule_cls()
                for issue in rule_instance.check(con):
                    all_issues.append(_issue_to_dict(issue, con, target_url))
            except Exception as e:
                logger.debug("Rule %s failed (non-fatal): %s", rule_id, e)

        logger.info("Rules complete: %d issues found", len(all_issues))
    except Exception as e:
        logger.warning("SEO rules engine failed: %s", e)
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass

    return all_issues


def _issue_to_dict(issue: Issue, con: duckdb.DuckDBPyConnection, default_url: str) -> dict[str, Any]:
    """Convert an ``Issue`` to a dict suitable for our facts pipeline."""
    evidence = dict(issue.evidence or {})

    url = default_url
    if issue.url_id is not None:
        try:
            row = con.execute(
                "SELECT url FROM urls WHERE url_id = ?", [issue.url_id]
            ).fetchone()
            if row:
                url = row[0]
        except Exception:
            pass

    return {
        "rule_id": issue.rule_id,
        "severity": issue.severity,
        "category": issue.category,
        "message": issue.message,
        "url": url,
        "evidence": evidence,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }
