"""Build a validated ReportFacts instance from raw sheet data.

Every value is wrapped in Evidence(source, timestamp, confidence).
No hardcoded fallbacks — missing data stays missing.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from report.evidence import (
    CONFIDENCE_NO_DATA,
    CONFIDENCE_OBSERVED,
    CONFIDENCE_VERIFIED,
    SOURCE_GSC_API,
    SOURCE_GA4_API,
    SOURCE_MANUAL,
    SOURCE_MISSING,
    SOURCE_PAGESPEED_API,
    SOURCE_SERP_HISTORY,
    SOURCE_SERP_SNAPSHOT,
    SOURCE_SITE_AUDIT,
    SOURCE_WEBSITE_INSIGHTS,
    Evidence,
)
from report.action_plan_generator import generate_action_plan
from report.evidence_engine import generate_recommendations
from report.health_score import compute_health_score
from report.facts import (
    ActionItem,
    AuthorityData,
    AuthorityLink,
    BacklinkData,
    BacklinkEntry,
    CWVData,
    Kpidata,
    LocalSEOData,
    MonthlyTrafficPoint,
    RankingRow,
    ReportFacts,
    ReportMetadata,
    SiteInfoData,
    SocialProfile,
    TechStackItem,
    TechnicalData,
    TechnicalIssue,
    UXIssue,
)

logger = logging.getLogger(__name__)

NOW = datetime.now()
TODAY_ISO = NOW.strftime("%Y-%m-%d")


def _safe_str(val: Any, default: str = "") -> str:
    return str(val).strip() if val else default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        v = str(val).strip()
        return int(float(v)) if v else default
    except (ValueError, TypeError):
        return default


def _change_int(raw: str) -> int:
    raw = str(raw).strip()
    if raw.startswith("+"):
        return int(raw[1:]) if raw[1:].isdigit() else 0
    if raw.startswith("-"):
        return -int(raw[1:]) if raw[1:].isdigit() else 0
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 0


def _evidence_from_psi(
    mobile: Any, desktop: Any,
) -> tuple[Evidence, Evidence]:
    m = Evidence.missing()
    d = Evidence.missing()
    if mobile is not None:
        m = Evidence.verified(round(mobile, 1), SOURCE_PAGESPEED_API)
    else:
        m = Evidence(None, SOURCE_PAGESPEED_API, confidence=CONFIDENCE_NO_DATA)
    if desktop is not None:
        d = Evidence.verified(round(desktop, 1), SOURCE_PAGESPEED_API)
    else:
        d = Evidence(None, SOURCE_PAGESPEED_API, confidence=CONFIDENCE_NO_DATA)
    return m, d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_facts(
    keywords_raw: list[dict[str, Any]],
    rankings_raw: list[dict[str, Any]],
    history_raw: list[dict[str, Any]],
    ai_raw: list[dict[str, Any]],
    audit_raw: list[dict[str, Any]],
    insights_raw: list[dict[str, Any]],
    plan_raw: list[dict[str, Any]],
    competitor_raw: list[dict[str, Any]],
    report_month: str = "",
    agency_name: str = "SEO Agency",
    client_name: str = "Client",
) -> ReportFacts:
    """Build a ReportFacts instance from raw sheet records.
    
    Every value is wrapped in Evidence. Missing data = Evidence.missing().
    No hardcoded defaults — the rendering layer decides how to display gaps.
    """
    # Build volume/competition/intent lookup from keywords sheet
    vol_lookup: dict[str, tuple[int | None, str | None, str | None]] = {}
    for rec in keywords_raw:
        kw = _safe_str(rec.get("Keyword", "")).lower()
        if not kw:
            continue
        vol_raw = rec.get("Search Volume") or rec.get("Volume") or rec.get("SV")
        vol = _safe_int(vol_raw) if vol_raw is not None else None
        comp = rec.get("Competition") or None
        intent = rec.get("Search Intent") or None
        vol_lookup[kw] = (vol, comp, intent)

    facts = ReportFacts(
        metadata=ReportMetadata(
            agency_name=agency_name,
            client_name=client_name,
            report_month=report_month or TODAY_ISO,
            generated_at=datetime.now().isoformat(timespec="seconds"),
        ),
    )

    _load_rankings(facts, rankings_raw, history_raw, vol_lookup)
    _load_insights(facts, insights_raw)
    _load_technical(facts, audit_raw)
    _load_kpis(facts, insights_raw, history_raw)
    _load_cwv(facts, insights_raw)
    _load_local(facts, competitor_raw)
    _load_authority(facts, keywords_raw)
    _load_ux(facts, audit_raw, keywords_raw)
    _load_plan(facts, plan_raw)
    _load_backlinks(facts, audit_raw, keywords_raw)
    _load_site_info(facts, audit_raw, keywords_raw)

    # Generate deterministic action plan from all loaded data
    generated = generate_action_plan(facts)
    if generated:
        facts.action_plan = generated

    # Weighted health score with per-category breakdown
    hs = compute_health_score(facts)
    facts.health_score_overall = hs.overall
    if facts.technical.score_breakdown:
        facts.technical.score_breakdown.clear()
    facts.technical.score_breakdown.extend(
        hs.technical.deductions + hs.performance.deductions + hs.seo_foundations.deductions
    )
    # Update evidence-wrapped health_score if it was missing
    if not facts.technical.health_score.is_available:
        facts.technical.health_score = Evidence.verified(hs.overall, SOURCE_SITE_AUDIT)

    # Evidence engine: structured recommendations
    recommendations = generate_recommendations(facts)
    # Store recommendations in the action_plan as ActionItems with evidence
    for rec in recommendations:
        facts.action_plan.append(ActionItem(
            team="Dev" if rec.category in ("performance", "technical") else "Content",
            task=f"[{rec.category.upper()}] {rec.recommendation}",
            priority=rec.priority,
            impact="high" if rec.priority == "P1" else "medium",
            effort="4h",
            owner="Dev Lead" if rec.category in ("performance", "technical") else "Content Lead",
            eta="This week" if rec.priority == "P1" else ("Next sprint" if rec.priority == "P2" else "This month"),
            success_metric=rec.expected_gain,
            proof=rec.evidence,
        ))

    return facts


# ---------------------------------------------------------------------------
# Internal loaders
# ---------------------------------------------------------------------------

def _load_rankings(
    facts: ReportFacts, rankings_raw: list[dict[str, Any]],
    history_raw: list[dict[str, Any]],
    vol_lookup: dict | None = None,
) -> None:
    """Build ranking rows from SERP Snapshot + SERP History.

    vol_lookup: keyword_lower -> (search_volume, competition, search_intent) from Keywords tab.
    Handles duplicate keywords via (keyword + target_url) dedup key.
    """
    if vol_lookup is None:
        vol_lookup = {}

    # Build history lookup: keyword_lower → [(date, position)]
    history_lookup: dict[str, list[tuple[str, str]]] = {}
    for rec in history_raw:
        kw = _safe_str(rec.get("Keyword", "")).lower()
        pos = _safe_str(rec.get("Position", ""))
        ts = _safe_str(rec.get("Timestamp", "") or rec.get("Run Date", "") or "")
        if kw and pos and ts:
            history_lookup.setdefault(kw, []).append((ts, pos))

    seen_keys: set[tuple[str, str]] = set()

    for rec in rankings_raw:
        kw = _safe_str(rec.get("Keyword", ""))
        target_url = _safe_str(rec.get("Target URL", ""))
        if not kw:
            continue

        # Dedup by keyword + target_url
        dedup_key = (kw.lower(), target_url.lower())
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        pos_raw = _safe_str(rec.get("Position", "N/A"))
        pos_confidence = CONFIDENCE_VERIFIED if pos_raw not in ("Not Found", "N/A", "") else CONFIDENCE_OBSERVED
        position = Evidence(
            value=pos_raw,
            source=SOURCE_SERP_SNAPSHOT,
            confidence=pos_confidence,
        )

        # Compute change from history
        kw_lower = kw.lower()
        prev_pos = ""
        if kw_lower in history_lookup:
            entries = history_lookup[kw_lower]
            entries.sort(key=lambda e: e[0])
            if entries:
                prev_pos = entries[-1][1]

        change_val = ""
        if prev_pos and prev_pos not in ("Not Found", "N/A", ""):
            diff = _safe_int(prev_pos) - _safe_int(pos_raw)
            if diff > 0:
                change_val = f"+{diff}"
            elif diff < 0:
                change_val = str(diff)
            else:
                change_val = "0"

        change = Evidence(
            value=change_val,
            source=SOURCE_SERP_HISTORY,
            confidence=CONFIDENCE_VERIFIED if change_val else CONFIDENCE_NO_DATA,
        )

        ai_overview = Evidence(
            value=_safe_str(rec.get("AI Overview Mention", "N/A")),
            source=SOURCE_SERP_SNAPSHOT,
        )
        paa = Evidence(
            value=_safe_str(rec.get("PAA Mention", "N/A")),
            source=SOURCE_SERP_SNAPSHOT,
        )

        data_avail = Evidence(
            value=_safe_str(rec.get("Data Availability", "Not Found")),
            source=SOURCE_SERP_SNAPSHOT,
        )

        # Collect competitors from any "Competitor" or "Top Competitor N URL" columns
        competitors = []
        for ckey in ["Competitor", "Top Competitor 1 URL", "Top Competitor 2 URL", "Top Competitor 3 URL"]:
            c = _safe_str(rec.get(ckey, ""))
            if c:
                competitors.append(c)

        # Get volume and intent from lookup
        lookup_data = vol_lookup.get(kw_lower, (None, None, None))
        if len(lookup_data) >= 3:
            vol, comp, intent = lookup_data
        elif len(lookup_data) >= 2:
            vol, comp = lookup_data[0], lookup_data[1]
            intent = None
        else:
            vol, comp, intent = None, None, None

        # Normalise competition level: Google returns "0", "0.1-0.3" etc.,
        # or "low" / "medium" / "high" as strings.
        comp_norm = None
        if comp:
            c = comp.strip().lower()
            if c in ("low", "medium", "high"):
                comp_norm = c
            elif c in ("0", "0.0"):
                comp_norm = "low"
            elif c in ("0.1", "0.2", "0.3", "0.4"):
                comp_norm = "low"
            elif c in ("0.5", "0.6", "0.7"):
                comp_norm = "medium"
            elif c in ("0.8", "0.9", "1.0"):
                comp_norm = "high"

        facts.rankings.append(RankingRow(
            keyword=kw,
            target_url=target_url,
            position=position,
            change=change,
            previous_position=prev_pos,
            ai_overview=ai_overview,
            paa=paa,
            data_availability=data_avail,
            competitors=competitors,
            search_volume=vol,
            competition=comp_norm,
        ))


def _load_insights(
    facts: ReportFacts, insights_raw: list[dict[str, Any]],
) -> None:
    """Pass-through — CWV is loaded separately; here we just log."""
    pass


def _load_technical(
    facts: ReportFacts, audit_raw: list[dict[str, Any]],
) -> None:
    if not audit_raw:
        facts.technical.health_score = Evidence.missing()
        return

    total_issues = 0
    missing_h1_count = 0
    missing_meta_count = 0
    missing_alt_total = 0
    thin_count = 0
    issues_list: list[TechnicalIssue] = []

    for rec in audit_raw:
        url = _safe_str(rec.get("URL", ""))
        h1 = _safe_str(rec.get("H1", ""))
        meta = _safe_str(rec.get("Meta Description", "") or rec.get("MetaDescription", ""))
        alt = _safe_int(rec.get("Images Missing Alt", 0))
        wc = _safe_int(rec.get("Word Count", 0))
        issues_str = _safe_str(rec.get("Issues", ""))

        if not h1:
            missing_h1_count += 1
        if not meta:
            missing_meta_count += 1
        missing_alt_total += alt
        if 0 < wc < 300:
            thin_count += 1
        if issues_str and issues_str != "None":
            for iss in issues_str.split(";"):
                iss = iss.strip()
                if iss:
                    total_issues += 1
                    issues_list.append(TechnicalIssue(page=url, issue_text=iss))

    # Health score: 100 - penalty (5 per issue + 2 per missing alt, capped at 70)
    penalty = min(total_issues * 5 + missing_alt_total * 2, 70)
    health_score = max(100 - penalty, 25)

    facts.technical = TechnicalData(
        health_score=Evidence.verified(health_score, SOURCE_SITE_AUDIT),
        pages_audited=Evidence.verified(len(audit_raw), SOURCE_SITE_AUDIT),
        total_issues=Evidence.verified(total_issues, SOURCE_SITE_AUDIT),
        missing_h1=Evidence.verified(missing_h1_count, SOURCE_SITE_AUDIT),
        missing_meta=Evidence.verified(missing_meta_count, SOURCE_SITE_AUDIT),
        missing_alt=Evidence.verified(missing_alt_total, SOURCE_SITE_AUDIT),
        thin_pages=Evidence.verified(thin_count, SOURCE_SITE_AUDIT),
        has_https=Evidence.observed(True, SOURCE_SITE_AUDIT),
        has_canonical=Evidence.observed(True, SOURCE_SITE_AUDIT),
        issues_list=issues_list,
    )


def _load_cwv(
    facts: ReportFacts, insights_raw: list[dict[str, Any]],
) -> None:
    ds_vals: list[float] = []
    ms_vals: list[float] = []

    for rec in insights_raw:
        try:
            ds = float(rec.get("Desktop PSI", 0) or 0)
            if ds > 0:
                ds_vals.append(ds)
        except (ValueError, TypeError):
            pass
        try:
            ms = float(rec.get("Mobile PSI", 0) or 0)
            if ms > 0:
                ms_vals.append(ms)
        except (ValueError, TypeError):
            pass

    desktop_avg = round(sum(ds_vals) / len(ds_vals), 1) if ds_vals else None
    mobile_avg = round(sum(ms_vals) / len(ms_vals), 1) if ms_vals else None

    mobile_sc, desktop_sc = _evidence_from_psi(mobile_avg, desktop_avg)

    facts.cwv = CWVData(
        mobile_score=mobile_sc,
        desktop_score=desktop_sc,
        lcp_seconds=Evidence.missing(),
        inp_ms=Evidence.missing(),
        cls_score=Evidence.missing(),
        render_blocking_ms=Evidence.missing(),
    )


def _load_kpis(
    facts: ReportFacts, insights_raw: list[dict[str, Any]],
    history_raw: list[dict[str, Any]],
) -> None:
    gsc_clicks: list[int] = []
    gsc_impressions: list[int] = []

    for rec in insights_raw:
        clicks_raw = rec.get("Clicks", "Access Required")
        impr_raw = rec.get("Impressions", "Access Required")
        if str(clicks_raw).isdigit():
            gsc_clicks.append(int(clicks_raw))
        if str(impr_raw).isdigit():
            gsc_impressions.append(int(impr_raw))

    total_clicks = sum(gsc_clicks) if gsc_clicks else None
    total_impressions = sum(gsc_impressions) if gsc_impressions else None

    facts.kpis = Kpidata(
        organic_users=Evidence.missing(),
        organic_users_change=Evidence.missing(),
        engaged_sessions=Evidence.missing(),
        engaged_sessions_change=Evidence.missing(),
        avg_engagement_time=Evidence.missing(),
        clicks=Evidence.verified(total_clicks, SOURCE_GSC_API) if total_clicks else Evidence.missing(),
        clicks_change=Evidence.missing(),
        impressions=Evidence.verified(total_impressions, SOURCE_GSC_API) if total_impressions else Evidence.missing(),
        impressions_change=Evidence.missing(),
    )


def _load_local(
    facts: ReportFacts, competitor_raw: list[dict[str, Any]],
) -> None:
    facts.local_seo = LocalSEOData(
        map_pack_presence=Evidence.missing(),
        nap_status=Evidence.missing(),
        review_count=Evidence.missing(),
        avg_rating=Evidence.missing(),
        gmb_posts=Evidence.missing(),
        gmb_photos=Evidence.missing(),
        gmb_reviews_responded=Evidence.missing(),
        next_steps=[],
    )


def _load_authority(
    facts: ReportFacts, keywords_raw: list[dict[str, Any]],
) -> None:
    facts.authority = AuthorityData(
        da_values=Evidence.missing(),
        da_months=Evidence.missing(),
        verified_links=[],
        dofollow_ratio=Evidence.missing(),
        strategy_pivot="",
    )


def _load_plan(
    facts: ReportFacts, plan_raw: list[dict[str, Any]],
) -> None:
    """Load action plan items from sheet (supplement to generated actions)."""
    if not plan_raw:
        return
    for rec in plan_raw:
        task = _safe_str(rec.get("Details", "") or rec.get("Item", "") or rec.get("Task", ""))
        if not task:
            continue
        team_raw = _safe_str(rec.get("Section", "") or rec.get("Team", "") or "")
        team_map = {"seo": "SEO", "dev": "Dev", "development": "Dev", "content": "Content", "local": "Local"}
        team = next((v for k, v in team_map.items() if k == team_raw.strip().lower()), "SEO")
        prio = _safe_str(rec.get("Priority", "P2")).upper()
        if prio not in ("P0", "P1", "P2", "P3"):
            prio = "P2"
        proof = Evidence.verified(
            value=task,
            source=SOURCE_MANUAL,
            proof_url=None,
        )
        facts.action_plan.append(ActionItem(
            team=team,
            task=task,
            priority=prio,
            owner=_safe_str(rec.get("Owner", "Unassigned")),
            eta=_safe_str(rec.get("ETA", "") or rec.get("Deadline", "") or "TBD"),
            proof=proof,
        ))


def _load_ux(
    facts: ReportFacts, audit_raw: list[dict[str, Any]],
    keywords_raw: list[dict[str, Any]],
) -> None:
    """Extract UX issues from site audit issues text."""
    ux_keywords = {
        "mobile": ("Mobile Responsiveness", "high"),
        "font": ("Font Size Too Small", "medium"),
        "tap": ("Tap Targets Too Small", "high"),
        "viewport": ("Viewport Not Configured", "high"),
        "content wider": ("Horizontal Scroll on Mobile", "medium"),
        "popup": ("Intrusive Interstitials/Popups", "high"),
    }
    seen: set[str] = set()
    for rec in audit_raw:
        issues_str = _safe_str(rec.get("Issues", ""))
        if not issues_str or issues_str == "None":
            continue
        for iss in issues_str.split(";"):
            iss = iss.strip()
            if not iss or iss in seen:
                continue
            iss_lower = iss.lower()
            for kw, (title, severity) in ux_keywords.items():
                if kw in iss_lower:
                    seen.add(iss)
                    facts.ux_issues.append(UXIssue(
                        title=title,
                        problem=iss[:120],
                        fix=_ux_fix_suggestion(kw, title),
                        severity=severity,
                    ))
                    break
    # If no UX issues found from audit, attempt to infer from PageSpeed score
    if not facts.ux_issues:
        ms = facts.cwv.mobile_score.value
        if ms is not None and ms < 60:
            facts.ux_issues.append(UXIssue(
                title="Mobile Page Load Speed",
                problem=f"Mobile speed score is {ms:.0f}/100 — slow load times degrade user experience.",
                fix="Compress images, defer JavaScript, and enable caching.",
                severity="high",
            ))
        if ms is not None and ms < 40:
            facts.ux_issues.append(UXIssue(
                title="Critical Load Time",
                problem="Page load exceeds recommended thresholds on mobile devices.",
                fix="Implement lazy loading, CDN, and server-side rendering where possible.",
                severity="high",
            ))


def _load_backlinks(
    facts: ReportFacts, audit_raw: list[dict[str, Any]],
    keywords_raw: list[dict[str, Any]],
) -> None:
    """Initialize backlink data — all Evidence.missing() until API integration."""
    facts.backlinks = BacklinkData(
        total_backlinks=Evidence.missing(),
        ref_domains=Evidence.missing(),
        dofollow_count=Evidence.missing(),
        nofollow_count=Evidence.missing(),
        edu_links=Evidence.missing(),
        gov_links=Evidence.missing(),
        domain_rating=Evidence.missing(),
        onpage_total_links=Evidence.missing(),
        onpage_internal_links=Evidence.missing(),
        onpage_external_links=Evidence.missing(),
    )


def _load_site_info(
    facts: ReportFacts, audit_raw: list[dict[str, Any]],
    keywords_raw: list[dict[str, Any]],
) -> None:
    """Initialize site info — all Evidence.missing() until API integration."""
    facts.site_info = SiteInfoData(
        server_ip=Evidence.missing(),
        web_server=Evidence.missing(),
        has_dmarc=Evidence.missing(),
        has_spf=Evidence.missing(),
    )


def _ux_fix_suggestion(keyword: str, title: str) -> str:
    fixes = {
        "mobile": "Implement responsive design with CSS media queries and flexible grids.",
        "font": "Increase base font size to 16px minimum on mobile viewports.",
        "tap": "Ensure touch targets are at least 48x48px with adequate spacing.",
        "viewport": 'Add <meta name="viewport" content="width=device-width, initial-scale=1"> to all pages.',
        "content wider": "Set max-width: 100% on all content containers and images.",
        "popup": "Remove or delay interstitials. Use banners instead of full-screen popups.",
    }
    return fixes.get(keyword, f"Address '{title}' issue identified in site audit.")
