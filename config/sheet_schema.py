"""Centralised sheet tab name definitions.

Single source of truth for tab name → data key mappings used across the
codebase. Import ``TabName`` and ``TAB_TO_KEY`` instead of hardcoding
string literals.
"""
from __future__ import annotations

from enum import Enum


class TabName(str, Enum):
    """Google Sheets tab names used by the pipeline.

    Each member's value is the exact sheet tab title.
    """
    KEYWORDS = "Keywords"
    SERP_SNAPSHOT = "SERP Snapshot"
    SERP_HISTORY = "SERP History"
    AI_ANALYSIS = "AI Analysis"
    SITE_AUDIT = "Site Audit"
    WEBSITE_INSIGHTS = "Website Tracking & Insights"
    MONTHLY_SEO_PLAN = "Monthly SEO Plan"
    COMPETITOR_SNAPSHOT = "Competitor Snapshot"


TAB_TO_KEY: dict[TabName, str] = {
    TabName.KEYWORDS: "keywords_raw",
    TabName.SERP_SNAPSHOT: "rankings_raw",
    TabName.SERP_HISTORY: "history_raw",
    TabName.AI_ANALYSIS: "ai_raw",
    TabName.SITE_AUDIT: "audit_raw",
    TabName.WEBSITE_INSIGHTS: "insights_raw",
    TabName.MONTHLY_SEO_PLAN: "plan_raw",
    TabName.COMPETITOR_SNAPSHOT: "competitor_raw",
}
