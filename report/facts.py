from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from report.evidence import Evidence

REPORT_SCHEMA_VERSION = "1.0.0"
"""Schema version for ReportFacts.
Increment when adding/removing fields so older reports still render.
v1.0.0 — Initial evidence-layer release.
"""


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
@dataclass
class ReportMetadata:
    agency_name: str = ""
    client_name: str = ""
    report_month: str = ""
    generated_at: str = ""
    pipeline_run_id: str = ""
    schema_version: str = REPORT_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
@dataclass
class MonthlyTrafficPoint:
    month: str
    users: Evidence = field(default_factory=Evidence.missing)


@dataclass
class Kpidata:
    organic_users: Evidence = field(default_factory=Evidence.missing)
    organic_users_change: Evidence = field(default_factory=Evidence.missing)
    sessions: Evidence = field(default_factory=Evidence.missing)
    engaged_sessions: Evidence = field(default_factory=Evidence.missing)
    engaged_sessions_change: Evidence = field(default_factory=Evidence.missing)
    avg_engagement_time: Evidence = field(default_factory=Evidence.missing)
    clicks: Evidence = field(default_factory=Evidence.missing)
    clicks_change: Evidence = field(default_factory=Evidence.missing)
    impressions: Evidence = field(default_factory=Evidence.missing)
    impressions_change: Evidence = field(default_factory=Evidence.missing)
    monthly_traffic: list[MonthlyTrafficPoint] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core Web Vitals
# ---------------------------------------------------------------------------
@dataclass
class CWVData:
    mobile_score: Evidence = field(default_factory=Evidence.missing)
    desktop_score: Evidence = field(default_factory=Evidence.missing)
    lcp_seconds: Evidence = field(default_factory=Evidence.missing)
    inp_ms: Evidence = field(default_factory=Evidence.missing)
    cls_score: Evidence = field(default_factory=Evidence.missing)
    render_blocking_ms: Evidence = field(default_factory=Evidence.missing)


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------
@dataclass
class RankingRow:
    keyword: str
    target_url: str = ""
    position: Evidence = field(default_factory=Evidence.missing)
    change: Evidence = field(default_factory=Evidence.missing)
    previous_position: str = ""
    ai_overview: Evidence = field(default_factory=Evidence.missing)
    paa: Evidence = field(default_factory=Evidence.missing)
    data_availability: Evidence = field(default_factory=Evidence.missing)
    competitors: list[str] = field(default_factory=list)
    # Priority engine fields (optional, sheet-driven)
    search_volume: int | None = None
    competition: str | None = None  # "low" | "medium" | "high"


# ---------------------------------------------------------------------------
# Technical SEO
# ---------------------------------------------------------------------------
@dataclass
class TechnicalIssue:
    page: str = ""
    issue_text: str = ""
    severity: str = "medium"


@dataclass
class TechnicalData:
    health_score: Evidence = field(default_factory=Evidence.missing)
    pages_audited: Evidence = field(default_factory=Evidence.missing)
    total_issues: Evidence = field(default_factory=Evidence.missing)
    missing_h1: Evidence = field(default_factory=Evidence.missing)
    missing_meta: Evidence = field(default_factory=Evidence.missing)
    missing_alt: Evidence = field(default_factory=Evidence.missing)
    thin_pages: Evidence = field(default_factory=Evidence.missing)
    has_https: Evidence = field(default_factory=Evidence.missing)
    has_canonical: Evidence = field(default_factory=Evidence.missing)
    has_schema: Evidence = field(default_factory=Evidence.missing)
    issues_list: list[TechnicalIssue] = field(default_factory=list)
    # Per-category breakdown from weighted scoring
    score_breakdown: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# GMB Keyword Position Tracking
# ---------------------------------------------------------------------------
@dataclass
class GMBKeywordRow:
    keyword: str = ""
    dates: list[str] = field(default_factory=list)
    positions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Local SEO
# ---------------------------------------------------------------------------
@dataclass
class LocalSEOData:
    map_pack_presence: Evidence = field(default_factory=Evidence.missing)
    nap_status: Evidence = field(default_factory=Evidence.missing)
    review_count: Evidence = field(default_factory=Evidence.missing)
    avg_rating: Evidence = field(default_factory=Evidence.missing)
    gmb_posts: Evidence = field(default_factory=Evidence.missing)
    gmb_photos: Evidence = field(default_factory=Evidence.missing)
    gmb_reviews_responded: Evidence = field(default_factory=Evidence.missing)
    gmb_observations: list[str] = field(default_factory=list)
    gmb_content_note: str = ""
    next_steps: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Authority (verified only)
# ---------------------------------------------------------------------------
@dataclass
class AuthorityLink:
    domain: str = ""
    url: str = ""
    dofollow: bool = False
    proof: Evidence = field(default_factory=Evidence.missing)


@dataclass
class AuthorityData:
    da_values: Evidence = field(default_factory=Evidence.missing)
    da_months: Evidence = field(default_factory=Evidence.missing)
    verified_links: list[AuthorityLink] = field(default_factory=list)
    dofollow_ratio: Evidence = field(default_factory=Evidence.missing)
    strategy_pivot: str = ""


# ---------------------------------------------------------------------------
# UX Issues
# ---------------------------------------------------------------------------
@dataclass
class UXIssue:
    title: str = ""
    problem: str = ""
    fix: str = ""
    severity: str = "medium"


# ---------------------------------------------------------------------------
# Action Plan
# ---------------------------------------------------------------------------
@dataclass
class ActionItem:
    team: str = ""   # SEO | Dev | Content | Local
    task: str = ""
    priority: str = "P2"  # P0 | P1 | P2
    impact: str = "medium"
    effort: str = "4h"
    owner: str = "Unassigned"
    dependency: str | None = None
    eta: str = "TBD"
    success_metric: str = ""
    proof: Evidence = field(default_factory=Evidence.missing)
    status: str = "todo"  # todo | in_progress | done | blocked | cancelled


# ---------------------------------------------------------------------------
# Backlink Profile
# ---------------------------------------------------------------------------
@dataclass
class BacklinkEntry:
    domain: str = ""
    title: str = ""
    da_score: str = ""


@dataclass
class BacklinkData:
    status: str = "MISSING"
    total_backlinks: Evidence = field(default_factory=Evidence.missing)
    ref_domains: Evidence = field(default_factory=Evidence.missing)
    dofollow_count: Evidence = field(default_factory=Evidence.missing)
    nofollow_count: Evidence = field(default_factory=Evidence.missing)
    edu_links: Evidence = field(default_factory=Evidence.missing)
    gov_links: Evidence = field(default_factory=Evidence.missing)
    top_backlinks: list[BacklinkEntry] = field(default_factory=list)
    top_pages: list[tuple[str, str]] = field(default_factory=list)
    top_anchors: list[tuple[str, str]] = field(default_factory=list)
    top_tlds: list[tuple[str, str]] = field(default_factory=list)
    top_countries: list[tuple[str, str]] = field(default_factory=list)
    domain_rating: Evidence = field(default_factory=Evidence.missing)
    onpage_total_links: Evidence = field(default_factory=Evidence.missing)
    onpage_internal_links: Evidence = field(default_factory=Evidence.missing)
    onpage_external_links: Evidence = field(default_factory=Evidence.missing)


# ---------------------------------------------------------------------------
# Site Info (tech stack, social, server)
# ---------------------------------------------------------------------------
@dataclass
class TechStackItem:
    name: str = ""
    version: str = ""
    category: str = ""


@dataclass
class SocialProfile:
    platform: str = ""
    handle: str = ""
    url: str = ""


@dataclass
class SiteInfoData:
    tech_stack: list[TechStackItem] = field(default_factory=list)
    social_profiles: list[SocialProfile] = field(default_factory=list)
    server_ip: Evidence = field(default_factory=Evidence.missing)
    web_server: Evidence = field(default_factory=Evidence.missing)
    dns_servers: list[str] = field(default_factory=list)
    has_dmarc: Evidence = field(default_factory=Evidence.missing)
    has_spf: Evidence = field(default_factory=Evidence.missing)
    # Page-level SEO metrics (populated from Playwright render)
    title_tag: str = ""
    meta_description: str = ""
    h1_count: int = 0
    h1_texts: list[str] = field(default_factory=list)
    word_count: int = 0
    # Marketing & Usability
    has_og_tags: Evidence = field(default_factory=Evidence.missing)
    has_robots_txt: Evidence = field(default_factory=Evidence.missing)
    has_sitemap_xml: Evidence = field(default_factory=Evidence.missing)


# ---------------------------------------------------------------------------
# Top-level container
# ---------------------------------------------------------------------------
@dataclass
class ReportFacts:
    metadata: ReportMetadata = field(default_factory=ReportMetadata)
    kpis: Kpidata = field(default_factory=Kpidata)
    cwv: CWVData = field(default_factory=CWVData)
    rankings: list[RankingRow] = field(default_factory=list)
    technical: TechnicalData = field(default_factory=TechnicalData)
    local_seo: LocalSEOData = field(default_factory=LocalSEOData)
    authority: AuthorityData = field(default_factory=AuthorityData)
    backlinks: BacklinkData = field(default_factory=BacklinkData)
    site_info: SiteInfoData = field(default_factory=SiteInfoData)
    ux_issues: list[UXIssue] = field(default_factory=list)
    action_plan: list[ActionItem] = field(default_factory=list)
    gmb_keywords: list[GMBKeywordRow] = field(default_factory=list)
    seo_activities_completed: list[str] = field(default_factory=list)
    way_forward: list[str] = field(default_factory=list)
    press_coverages: list[str] = field(default_factory=list)
    social_bookmarks: list[tuple[str, str, str]] = field(default_factory=list)
    image_submissions: list[tuple[str, str, str]] = field(default_factory=list)
    video_submissions: list[tuple[str, str, str]] = field(default_factory=list)
    executive_narrative: str = ""
    health_score_overall: int | None = None
    rankings_total_estimated: int = 0
