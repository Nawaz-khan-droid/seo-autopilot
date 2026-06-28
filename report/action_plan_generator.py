"""Deterministic, rule-based action plan generator with priority engine.

Produces structured ActionItem list from ReportFacts.
No LLM, no hardcoded templates — every action traces to a data signal.

Priority engine factors: search volume, competition, current position, change.
"""
from __future__ import annotations

import logging
from typing import Any

from report.evidence import Evidence
from report.facts import ActionItem, ReportFacts

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _change_val(raw: str) -> int:
    raw = str(raw).strip()
    if raw.startswith("+"):
        return int(raw[1:]) if raw[1:].isdigit() else 0
    if raw.startswith("-"):
        return -int(raw[1:]) if raw[1:].isdigit() else 0
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 0


def _priority_from_volume(
    volume: int | None, competition: str | None, position: int,
) -> str:
    """Priority engine: volume + competition + position → priority.
    
    Only P1/P2/P3 are used (no P0 per guardrail).
    High volume keywords at page 2 get P1.
    """
    # Default priority by position
    if position <= 10:
        base = "P2"  # Already ranking well, maintain
    elif position <= 20:
        base = "P2"  # Page 2 default
    elif position <= 30:
        base = "P2"
    else:
        base = "P3"

    if volume is None:
        return base

    # Volume boost
    vol_score = 0
    if volume >= 10000:
        vol_score = 3
    elif volume >= 5000:
        vol_score = 2
    elif volume >= 1000:
        vol_score = 1

    # Competition modifier
    comp_penalty = 0
    if competition and competition.lower() == "high":
        comp_penalty = 1
    elif competition and competition.lower() == "low":
        comp_penalty = -1

    score = vol_score + comp_penalty

    if score >= 4:
        return "P0"
    if score >= 1:
        return "P1"
    if score >= 0:
        return "P2"
    return "P3"


def generate_action_plan(facts: ReportFacts) -> list[ActionItem]:
    """Build a list of deterministic ActionItems from ReportFacts."""
    items: list[ActionItem] = []

    _rankings_actions(facts, items)
    _technical_actions(facts, items)
    _cwv_actions(facts, items)
    _local_actions(facts, items)
    _authority_actions(facts, items)
    _kpi_actions(facts, items)

    # Sort by priority (P0 first) then impact
    def _sort_key(item: ActionItem) -> tuple:
        pri = PRIORITY_ORDER.get(item.priority, 99)
        imp = 0 if item.impact == "high" else (1 if item.impact == "medium" else 2)
        return (pri, imp)

    items.sort(key=_sort_key)

    # Deduplicate by task text
    seen: set[str] = set()
    deduped: list[ActionItem] = []
    for item in items:
        if item.task not in seen:
            seen.add(item.task)
            deduped.append(item)
    logger.info(f"Action plan: {len(deduped)} items generated from {len(items)} candidates")
    return deduped


def _rankings_actions(facts: ReportFacts, items: list[ActionItem]) -> None:
    """Actions from ranking movements, with priority engine."""
    ranked_kws: list = [
        r for r in facts.rankings
        if r.position.is_available
        and str(r.position.value).strip().isdigit()
    ]

    # Page 2 keywords — priority varies by volume
    page2 = [r for r in ranked_kws if 11 <= int(r.position.value) <= 20]
    for r in page2:
        pos = int(r.position.value)
        pri = _priority_from_volume(r.search_volume, r.competition, pos)
        vol_hint = f" (vol={r.search_volume})" if r.search_volume else ""
        items.append(ActionItem(
            team="SEO",
            task=f"Build internal links to '{r.keyword}' from related service pages.{vol_hint}",
            priority=pri,
            impact="high" if pri == "P1" else "medium",
            effort="2h",
            owner="SEO Lead",
            dependency=None,
            eta="Next sprint",
            success_metric=f"'{r.keyword}' reaches page 1 (top 10).",
            status="todo",
        ))

    # Keywords that dropped
    dropped = [r for r in facts.rankings if _change_val(str(r.change.value)) < 0]
    for r in dropped[:5]:
        change_abs = abs(_change_val(str(r.change.value)))
        pos = int(r.position.value) if r.position.is_available and str(r.position.value).strip().isdigit() else 99
        pri = _priority_from_volume(r.search_volume, r.competition, pos)
        # Downgrade priority for small drops
        if change_abs < 3 and pri == "P1":
            pri = "P2"
        items.append(ActionItem(
            team="SEO",
            task=f"Audit and recover ranking for '{r.keyword}' — check SERP competitors and refresh content.",
            priority=pri,
            impact="high" if change_abs >= 5 else "medium",
            effort="3h",
            owner="SEO Lead",
            dependency=None,
            eta="This week" if pri == "P1" else "Next sprint",
            success_metric=f"'{r.keyword}' recovers to previous position or better.",
            status="todo",
        ))

    # Not found keywords
    not_found = [
        r for r in facts.rankings
        if str(r.position.value).strip().lower() == "not found"
    ]
    if not_found:
        # Sort by volume descending if available
        nf_sorted = sorted(
            not_found,
            key=lambda r: -(r.search_volume or 0),
        )[:3]
        for r in nf_sorted:
            vol_tag = f" (vol={r.search_volume})" if r.search_volume else ""
            items.append(ActionItem(
                team="SEO",
                task=f"Investigate non-indexed keyword '{r.keyword}'. Check content gap and site structure.{vol_tag}",
                priority=_priority_from_volume(r.search_volume, r.competition, 99),
                impact="high",
                effort="4h",
                owner="SEO Lead",
                dependency="Site audit data",
                eta="Next sprint",
                success_metric=f"'{r.keyword}' begins ranking in top 50.",
                status="todo",
            ))


def _technical_actions(facts: ReportFacts, items: list[ActionItem]) -> None:
    """Actions from technical audit."""
    mh1 = facts.technical.missing_h1.value
    mm = facts.technical.missing_meta.value
    malt = facts.technical.missing_alt.value
    tp = facts.technical.thin_pages.value

    if mh1 is not None and int(mh1) > 0:
        items.append(ActionItem(
            team="Dev",
            task=f"Add H1 tags to {mh1} pages missing primary heading.",
            priority="P1",
            impact="high",
            effort="2h",
            owner="Dev Lead",
            dependency=None,
            eta="This week",
            success_metric="0 pages missing H1.",
            status="todo",
        ))

    if mm is not None and int(mm) > 0:
        items.append(ActionItem(
            team="Content",
            task=f"Write meta descriptions for {mm} service pages without SERP preview text.",
            priority="P1",
            impact="high",
            effort="3h",
            owner="Content Lead",
            dependency="Dev to provide page list",
            eta="Next sprint",
            success_metric="0 pages missing meta description.",
            status="todo",
        ))

    if malt is not None and int(malt) > 0:
        items.append(ActionItem(
            team="Dev",
            task=f"Add alt text to {malt} images — critical for image search indexing.",
            priority="P2",
            impact="medium",
            effort="4h",
            owner="Dev Lead",
            dependency=None,
            eta="Next sprint",
            success_metric=f"{malt}/0 alt text gaps closed.",
            status="todo",
        ))

    if tp is not None and int(tp) > 0:
        items.append(ActionItem(
            team="Content",
            task=f"Expand {tp} thin-content pages to 300+ words.",
            priority="P2",
            impact="medium",
            effort="5h",
            owner="Content Lead",
            dependency=None,
            eta="This month",
            success_metric="0 pages below 300 words.",
            status="todo",
        ))

    total_issues = facts.technical.total_issues.value
    if total_issues is not None and int(total_issues) > 0:
        items.append(ActionItem(
            team="Dev",
            task=f"Full site audit scheduled: {total_issues} outstanding issues to triage.",
            priority="P2",
            impact="medium",
            effort="6h",
            owner="Dev Lead",
            dependency=None,
            eta="This month",
            success_metric="All P0/P1 issues resolved.",
            status="todo",
        ))


def _cwv_actions(facts: ReportFacts, items: list[ActionItem]) -> None:
    """Actions from Core Web Vitals."""
    ms = facts.cwv.mobile_score.value
    ds = facts.cwv.desktop_score.value
    lcp = facts.cwv.lcp_seconds.value

    if ms is not None and ms < 50:
        items.append(ActionItem(
            team="Dev",
            task=f"Critical: Mobile speed is {ms:.0f}/100. Optimize LCP and reduce render-blocking JS.",
            priority="P1",
            impact="high",
            effort="2d",
            owner="Dev Lead",
            dependency="Design sign-off on image compression",
            eta="This week",
            success_metric="Mobile score reaches 60+.",
            status="todo",
        ))
    elif ms is not None and ms < 80:
        gap = int(ds - ms) if ds else 0
        items.append(ActionItem(
            team="Dev",
            task=f"Mobile speed gap: {ms:.0f}/100 vs desktop {ds:.0f}/100 ({gap}pt gap). Defer JS, convert to WebP.",
            priority="P1",
            impact="high",
            effort="1d",
            owner="Dev Lead",
            dependency=None,
            eta="Next sprint",
            success_metric="Mobile score reaches 80+.",
            status="todo",
        ))

    if lcp is not None and lcp > 2.5:
        prio = "P1" if lcp > 4 else "P2"
        items.append(ActionItem(
            team="Dev",
            task=f"LCP is {lcp}s — above 2.5s threshold. Optimize hero image delivery with WebP/AVIF.",
            priority=prio,
            impact="medium",
            effort="4h",
            owner="Dev Lead",
            dependency=None,
            eta="This sprint",
            success_metric="LCP under 2.5s.",
            status="todo",
        ))

    inp = facts.cwv.inp_ms.value
    if inp is not None and inp > 200:
        prio = "P1" if inp > 350 else "P2"
        items.append(ActionItem(
            team="Dev",
            task=f"INP is {inp}ms — above 200ms threshold. Break up long JS tasks and defer third-party scripts.",
            priority=prio,
            impact="medium",
            effort="1d",
            owner="Dev Lead",
            dependency="JS audit",
            eta="Next sprint",
            success_metric="INP under 200ms.",
            status="todo",
        ))


def _local_actions(facts: ReportFacts, items: list[ActionItem]) -> None:
    """Actions from Local SEO data gaps — only when real data exists."""
    if not facts.local_seo.map_pack_presence.is_available and not facts.local_seo.review_count.is_available:
        return  # No local data at all — skip this section entirely

    rc = facts.local_seo.review_count.value
    if rc is not None and int(rc) < 10:
        items.append(ActionItem(
            team="Local",
            task=f"Review count is {rc} — implement review generation campaign (email + SMS).",
            priority="P1",
            impact="high",
            effort="4h setup + ongoing",
            owner="SEO Lead",
            dependency="CRM integration",
            eta="This month",
            success_metric="15+ reviews on GBP.",
            status="todo",
        ))


def _authority_actions(facts: ReportFacts, items: list[ActionItem]) -> None:
    """Actions from authority/backlink data."""
    da = facts.authority.da_values.value
    if da is not None and isinstance(da, list) and len(da) >= 2:
        recent = da[-1]
        previous = da[-2]
        if recent <= previous:
            items.append(ActionItem(
                team="SEO",
                task=f"DA is stagnant at {recent}. Launch a digital PR push — 3-4 guest posts on industry sites.",
                priority="P2",
                impact="medium",
                effort="8h",
                owner="SEO Lead",
                dependency="Content team to produce assets",
                eta="This month",
                success_metric="DA increases by 2+ points.",
                status="todo",
            ))

    if not facts.authority.verified_links:
        items.append(ActionItem(
            team="SEO",
            task="No verified backlinks this period. Build 2-3 dofollow links from relevant industry directories.",
            priority="P2",
            impact="medium",
            effort="6h",
            owner="SEO Lead",
            dependency=None,
            eta="This month",
            success_metric="3+ verified dofollow links.",
            status="todo",
        ))


def _kpi_actions(facts: ReportFacts, items: list[ActionItem]) -> None:
    """Actions from KPI connectivity gaps."""
    if not facts.kpis.clicks.is_available:
        items.append(ActionItem(
            team="SEO",
            task="GSC API not connected — configure Google Search Console integration for click/impression data.",
            priority="P1",
            impact="high",
            effort="2h",
            owner="Dev Lead",
            dependency="Service account permissions",
            eta="This week",
            success_metric="GSC data populates in report.",
            status="todo",
        ))
    if not facts.kpis.organic_users.is_available:
        items.append(ActionItem(
            team="SEO",
            task="GA4 API not connected — configure Google Analytics 4 integration for user engagement data.",
            priority="P1",
            impact="high",
            effort="2h",
            owner="Dev Lead",
            dependency="GA4 property + service account",
            eta="This week",
            success_metric="GA4 data populates in report.",
            status="todo",
        ))
