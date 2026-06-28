"""Weighted SEO health score with per-category breakdown.

Base = 100. Penalties are subtracted per category.
Every penalty is explained — no black-box scoring.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from report.facts import ReportFacts

logger = logging.getLogger(__name__)


@dataclass
class ScoreCategory:
    name: str
    score: int              # category score out of 100
    max_score: int = 100     # category weight
    deductions: list[str] = field(default_factory=list)


@dataclass
class HealthScoreResult:
    overall: int             # 0-100
    technical: ScoreCategory
    performance: ScoreCategory
    seo_foundations: ScoreCategory


def compute_health_score(facts: ReportFacts) -> HealthScoreResult:
    """Compute explainable health score with per-category breakdown."""
    deductions_tech: list[str] = []
    deductions_perf: list[str] = []
    deductions_seo: list[str] = []

    # ── Technical (weight: 40%) ──
    tech_penalty = 0.0

    mh1 = facts.technical.missing_h1.value
    if mh1 is not None and int(mh1) > 0:
        p = min(int(mh1) * 5, 25)
        tech_penalty += p
        deductions_tech.append(f"Missing H1 on {mh1} page(s): -{p}")

    mm = facts.technical.missing_meta.value
    if mm is not None and int(mm) > 0:
        p = min(int(mm) * 3, 15)
        tech_penalty += p
        deductions_tech.append(f"Missing meta description on {mm} page(s): -{p}")

    malt = facts.technical.missing_alt.value
    if malt is not None and int(malt) > 0:
        p = min(int(malt) * 2, 20)
        tech_penalty += p
        deductions_tech.append(f"Images missing alt text ({malt} total): -{p}")

    thin = facts.technical.thin_pages.value
    if thin is not None and int(thin) > 0:
        p = min(int(thin) * 3, 15)
        tech_penalty += p
        deductions_tech.append(f"Thin-content pages ({thin} under 300 words): -{p}")

    https = facts.technical.has_https.value
    if https is not None and not https:
        tech_penalty += 10
        deductions_tech.append("HTTPS not enabled: -10")

    canonical = facts.technical.has_canonical.value
    if canonical is not None and not canonical:
        tech_penalty += 5
        deductions_tech.append("Canonical tags missing: -5")

    tech_raw = max(100 - tech_penalty, 10)

    # ── Performance (weight: 35%) ──
    perf_penalty = 0.0

    lcp = facts.cwv.lcp_seconds.value
    if lcp is not None:
        if lcp > 8.0:
            perf_penalty += 12
            deductions_perf.append(f"LCP at {lcp}s (critical): -12")
        elif lcp > 4.0:
            perf_penalty += 8
            deductions_perf.append(f"LCP at {lcp}s (poor): -8")
        elif lcp > 2.5:
            perf_penalty += 4
            deductions_perf.append(f"LCP at {lcp}s (needs improvement): -4")

    inp = facts.cwv.inp_ms.value
    if inp is not None:
        if inp > 500:
            perf_penalty += 10
            deductions_perf.append(f"INP at {inp}ms (critical): -10")
        elif inp > 300:
            perf_penalty += 6
            deductions_perf.append(f"INP at {inp}ms (poor): -6")
        elif inp > 200:
            perf_penalty += 3
            deductions_perf.append(f"INP at {inp}ms (needs improvement): -3")

    cls_score = facts.cwv.cls_score.value
    if cls_score is not None:
        if cls_score > 0.5:
            perf_penalty += 8
            deductions_perf.append(f"CLS at {cls_score} (critical): -8")
        elif cls_score > 0.25:
            perf_penalty += 5
            deductions_perf.append(f"CLS at {cls_score} (poor): -5")
        elif cls_score > 0.1:
            perf_penalty += 2
            deductions_perf.append(f"CLS at {cls_score} (needs improvement): -2")

    rb = facts.cwv.render_blocking_ms.value
    if rb is not None:
        if rb > 500:
            perf_penalty += 5
            deductions_perf.append(f"Render-blocking resources ({rb}ms): -5")
        elif rb > 200:
            perf_penalty += 3
            deductions_perf.append(f"Render-blocking resources ({rb}ms): -3")

    ms = facts.cwv.mobile_score.value
    if ms is not None and ms < 50:
        perf_penalty += 5
        deductions_perf.append(f"Mobile speed score {ms:.0f}/100 (critical): -5")
    elif ms is not None and ms < 80:
        perf_penalty += 2
        deductions_perf.append(f"Mobile speed score {ms:.0f}/100 (below target): -2")

    perf_raw = max(100 - perf_penalty, 10)

    # ── SEO Foundations (weight: 25%) ──
    seo_penalty = 0.0

    dof = facts.authority.dofollow_ratio.value
    if dof is not None:
        try:
            ratio = float(dof.replace("%", "")) if isinstance(dof, str) else float(dof)
            if ratio < 30:
                seo_penalty += 8
                deductions_seo.append(f"Dofollow ratio {ratio:.0f}% (low): -8")
            elif ratio < 50:
                seo_penalty += 4
                deductions_seo.append(f"Dofollow ratio {ratio:.0f}% (moderate): -4")
        except (ValueError, TypeError):
            pass

    da = facts.authority.da_values.value
    if da is not None and isinstance(da, list) and len(da) >= 1:
        last_da = da[-1]
        try:
            ld = float(last_da)
            if ld < 20:
                seo_penalty += 6
                deductions_seo.append(f"DA {ld:.0f} (very low): -6")
            elif ld < 35:
                seo_penalty += 3
                deductions_seo.append(f"DA {ld:.0f} (low): -3")
        except (ValueError, TypeError):
            pass

    not_found = sum(
        1 for r in facts.rankings
        if str(r.position.value).strip().lower() == "not found"
    )
    if not_found > 0:
        p = min(not_found * 2, 10)
        seo_penalty += p
        deductions_seo.append(f"Keywords not ranking ({not_found}): -{p}")

    if not facts.authority.verified_links:
        seo_penalty += 4
        deductions_seo.append("No verified backlinks this period: -4")

    seo_raw = max(100 - seo_penalty, 10)

    # ── Weighted overall (tech 40%, perf 35%, seo 25%) ──
    overall = round(tech_raw * 0.40 + perf_raw * 0.35 + seo_raw * 0.25)

    return HealthScoreResult(
        overall=overall,
        technical=ScoreCategory("Technical", round(tech_raw), deductions=deductions_tech),
        performance=ScoreCategory("CWV & Speed", round(perf_raw), deductions=deductions_perf),
        seo_foundations=ScoreCategory("SEO Foundations", round(seo_raw), deductions=deductions_seo),
    )
