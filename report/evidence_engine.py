"""Recommendation Evidence Engine.

Transforms raw issues into structured, evidence-backed recommendations
with root cause, expected gain, and priority — not generic advice.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from report.evidence import (
    CONFIDENCE_ESTIMATED,
    CONFIDENCE_VERIFIED,
    SOURCE_PAGESPEED_API,
    SOURCE_SITE_AUDIT,
    Evidence,
)
from report.facts import ReportFacts

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    issue: str                  # "Homepage LCP = 5.0s"
    evidence: Evidence          # PSI Report, 2026-06-01
    root_cause: str             # "hero-banner.webp = 2.7MB"
    recommendation: str         # "Convert hero-banner.webp to AVIF"
    expected_gain: str          # "-1.4s LCP"
    priority: str               # "P1" | "P2" | "P3"
    category: str = "performance"  # "technical" | "performance" | "content" | "authority"


def generate_recommendations(facts: ReportFacts) -> list[Recommendation]:
    """Generate evidence-backed recommendations from all available data."""
    recs: list[Recommendation] = []

    _cwv_recommendations(facts, recs)
    _technical_recommendations(facts, recs)
    _content_recommendations(facts, recs)
    _authority_recommendations(facts, recs)

    # Deduplicate by issue text
    seen: set[str] = set()
    deduped: list[Recommendation] = []
    for r in recs:
        if r.issue not in seen:
            seen.add(r.issue)
            deduped.append(r)
    logger.info(f"Evidence engine: {len(deduped)} recommendations from {len(recs)} candidates")
    return deduped


def _cwv_recommendations(facts: ReportFacts, recs: list[Recommendation]) -> None:
    """CWV-based recommendations with root cause analysis."""
    lcp = facts.cwv.lcp_seconds.value
    if lcp is not None and lcp > 2.5:
        severity = "P1" if lcp > 4.0 else "P2"
        impact = round((lcp - 2.5) / lcp * 100)
        recs.append(Recommendation(
            issue=f"LCP = {lcp}s",
            evidence=Evidence.verified(lcp, SOURCE_PAGESPEED_API),
            root_cause="Uncompressed hero images, render-blocking JS, or slow server response",
            recommendation=(
                "Compress hero image to WebP/AVIF, defer non-critical JS, "
                "enable CDN caching"
            ),
            expected_gain=f"-{impact}% LCP (target <2.5s)",
            priority=severity,
            category="performance",
        ))

    inp = facts.cwv.inp_ms.value
    if inp is not None and inp > 200:
        severity = "P1" if inp > 350 else "P2"
        excess = round((inp - 200) / 200 * 100)
        recs.append(Recommendation(
            issue=f"INP = {inp}ms",
            evidence=Evidence.verified(inp, SOURCE_PAGESPEED_API),
            root_cause="Long main-thread tasks from heavy JavaScript bundles",
            recommendation=(
                "Break up long tasks (>50ms), lazy-load third-party scripts, "
                "defer non-critical JS"
            ),
            expected_gain=f"-{min(excess, 70)}% INP (target <200ms)",
            priority=severity,
            category="performance",
        ))

    cls_val = facts.cwv.cls_score.value
    if cls_val is not None and cls_val > 0.1:
        severity = "P1" if cls_val > 0.25 else "P2"
        recs.append(Recommendation(
            issue=f"CLS = {cls_val}",
            evidence=Evidence.verified(cls_val, SOURCE_PAGESPEED_API),
            root_cause="Missing explicit dimensions on images/embeds or dynamic content injection",
            recommendation=(
                "Set explicit width/height on all images and embeds, "
                "reserve space for dynamic ads"
            ),
            expected_gain=f"Target CLS <0.1",
            priority=severity,
            category="performance",
        ))

    rb = facts.cwv.render_blocking_ms.value
    if rb is not None and rb > 100:
        severity = "P1" if rb > 500 else "P2"
        recs.append(Recommendation(
            issue=f"Render-blocking resources delay = {rb}ms",
            evidence=Evidence.verified(rb, SOURCE_PAGESPEED_API),
            root_cause="CSS/JS files blocking first paint",
            recommendation="Inline critical CSS, defer non-critical CSS/JS, use `media` attributes",
            expected_gain=f"-{min(round(rb * 0.6), 300)}ms first paint",
            priority=severity,
            category="performance",
        ))


def _technical_recommendations(facts: ReportFacts, recs: list[Recommendation]) -> None:
    """Technical audit recommendations."""
    mh1 = facts.technical.missing_h1.value
    if mh1 is not None and int(mh1) > 0:
        recs.append(Recommendation(
            issue=f"{mh1} page(s) missing H1 tag",
            evidence=Evidence.verified(mh1, SOURCE_SITE_AUDIT),
            root_cause="CMS templates or new pages created without H1 field populated",
            recommendation=f"Add descriptive H1 tags to {mh1} pages — one H1 per page containing primary keyword",
            expected_gain="Improved heading structure for search bots and screen readers",
            priority="P1",
            category="technical",
        ))

    mm = facts.technical.missing_meta.value
    if mm is not None and int(mm) > 0:
        recs.append(Recommendation(
            issue=f"{mm} page(s) missing meta description",
            evidence=Evidence.verified(mm, SOURCE_SITE_AUDIT),
            root_cause="Service/pillar pages created without meta description template",
            recommendation=f"Write 155-160 character meta descriptions for {mm} pages with target keywords",
            expected_gain="Better CTR from SERP snippets",
            priority="P1",
            category="technical",
        ))

    malt = facts.technical.missing_alt.value
    if malt is not None and int(malt) > 0:
        recs.append(Recommendation(
            issue=f"{malt} images missing alt text",
            evidence=Evidence.verified(malt, SOURCE_SITE_AUDIT),
            root_cause="Images uploaded without alt attributes in CMS",
            recommendation=f"Add descriptive alt text to {malt} images — include target keywords where natural",
            expected_gain="Image search visibility + accessibility compliance",
            priority="P2",
            category="technical",
        ))

    # 404 detection from issues list
    broken_links = [
        iss for iss in facts.technical.issues_list
        if "404" in iss.issue_text or "broken" in iss.issue_text.lower() or "not found" in iss.issue_text.lower()
    ]
    if broken_links:
        recs.append(Recommendation(
            issue=f"{len(broken_links)} broken link(s) or 404 error(s) detected",
            evidence=Evidence.verified(len(broken_links), SOURCE_SITE_AUDIT),
            root_cause=f"Pages linking to removed/moved content: {broken_links[0].issue_text[:60]}",
            recommendation="Set up 301 redirects for broken URLs or restore deleted pages",
            expected_gain="Retain link equity and improve crawl budget",
            priority="P1",
            category="technical",
        ))


def _content_recommendations(facts: ReportFacts, recs: list[Recommendation]) -> None:
    """Content-focused recommendations from rankings."""
    page2 = [
        r for r in facts.rankings
        if r.position.is_available
        and str(r.position.value).strip().isdigit()
        and 11 <= int(r.position.value) <= 20
    ]
    # Pick highest-impact page 2 keyword (by priority engine: page value is hard to compute without volume)
    if page2:
        top = page2[0]
        recs.append(Recommendation(
            issue=f"'{top.keyword}' at position #{top.position.value} (page 2)",
            evidence=Evidence.observed(
                f"#{top.position.value}", SOURCE_SITE_AUDIT,
            ),
            root_cause="Content may lack depth, internal links, or keyword alignment vs page-1 competitors",
            recommendation=(
                f"Expand '{top.keyword}' page to 1500+ words, add FAQ schema, "
                f"build 2-3 internal links from related pages"
            ),
            expected_gain="Page 1 ranking (top 10) for a page-2 keyword",
            priority="P2",
            category="content",
        ))

    dropped = [
        r for r in facts.rankings
        if r.change.is_available and str(r.change.value).startswith("-")
    ]
    if dropped:
        worst = min(dropped, key=lambda r: int(str(r.change.value)))
        recs.append(Recommendation(
            issue=f"'{worst.keyword}' dropped {worst.change.value} positions",
            evidence=Evidence.verified(str(worst.change.value), SOURCE_SITE_AUDIT),
            root_cause="Competitor content refresh or algorithm shift for that query",
            recommendation=(
                f"Review '{worst.keyword}' SERP for new competitors, "
                f"refresh content with updated stats and internal links"
            ),
            expected_gain="Recover lost ranking position",
            priority="P1",
            category="content",
        ))


def _authority_recommendations(facts: ReportFacts, recs: list[Recommendation]) -> None:
    """Authority/off-page recommendations."""
    if not facts.authority.verified_links:
        recs.append(Recommendation(
            issue="No verified backlinks in this reporting period",
            evidence=Evidence.missing(),
            root_cause="No link-building campaign active or outreach not yet started",
            recommendation=(
                "Launch 2-week outreach: identify 10 industry-relevant sites, "
                "offer guest posts or resource page inclusions"
            ),
            expected_gain="3-5 dofollow backlinks from relevant domains",
            priority="P2",
            category="authority",
        ))

    local_gmb = facts.local_seo.gmb_posts.is_available
    if not local_gmb:
        recs.append(Recommendation(
            issue="Google Business Profile posts not tracked",
            evidence=Evidence.missing(),
            root_cause="GBP integration not configured or posts not published",
            recommendation="Set up GBP posting schedule: 1-2 posts per week with offers, events, or FAQs",
            expected_gain="Improved local pack presence and engagement signals",
            priority="P2",
            category="authority",
        ))
