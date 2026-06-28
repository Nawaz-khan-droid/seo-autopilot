"""LLM-powered SEO report generator.

Uses Groq (Llama 3 70B) to write a rich, executive-ready markdown report
from structured ReportFacts data. No pixel-painting — pure LLM prose.
"""

from __future__ import annotations

import logging
from typing import Any

from report.facts import ReportFacts

logger = logging.getLogger(__name__)


def _val(ev, fmt="str"):
    """Safely extract value from Evidence or return '—'."""
    if ev is None:
        return "—"
    if hasattr(ev, "is_available") and not ev.is_available:
        return "—"
    val = ev.value if hasattr(ev, "value") else ev
    if val is None:
        return "—"
    if fmt == "int":
        try:
            return str(int(val))
        except (ValueError, TypeError):
            return str(val)
    return str(val)


def _change_str(ev) -> str:
    raw = _val(ev)
    if raw in ("—", "", "0"):
        return "no change"
    try:
        v = int(raw)
        if v > 0:
            return f"improved by {v} positions"
        if v < 0:
            return f"dropped by {abs(v)} positions"
        return "no change"
    except (ValueError, TypeError):
        return raw if raw != "—" else "no change"


def _build_data_section(facts: ReportFacts) -> str:
    """Build a structured data prompt section from ReportFacts."""
    lines = []

    # ── Metadata ──
    m = facts.metadata
    lines.append("## CLIENT INFO")
    lines.append(f"Client: {m.client_name or 'N/A'}")
    lines.append(f"Agency: {m.agency_name or 'N/A'}")
    lines.append(f"Period: {m.report_month or 'N/A'}")
    lines.append("")

    # ── Rankings ──
    ranks = facts.rankings
    lines.append(f"## KEYWORD RANKINGS ({len(ranks)} tracked)")
    if ranks:
        lines.append("")
        lines.append("| Keyword | Current Pos | Change | Target URL |")
        lines.append("|---------|------------|--------|------------|")
        for r in ranks[:20]:
            pos = _val(r.position)
            chg = _change_str(r.change)
            lines.append(f"| {r.keyword[:40]} | {pos} | {chg} | {r.target_url[:50]} |")
        lines.append("")

        # Distribution
        total = len(ranks)
        p1 = sum(1 for r in ranks if _val(r.position).isdigit() and int(_val(r.position)) == 1)
        top3 = sum(1 for r in ranks if _val(r.position).isdigit() and int(_val(r.position)) <= 3)
        top10 = sum(1 for r in ranks if _val(r.position).isdigit() and int(_val(r.position)) <= 10)
        nf = sum(1 for r in ranks if _val(r.position).lower() == "not found")
        lines.append(f"Distribution: #{'1'}: {p1}, Top 3: {top3}, Top 10: {top10}, Not Found: {nf}")
        lines.append("")
    else:
        lines.append("No ranking data available.")
        lines.append("")

    # ── KPIs ──
    k = facts.kpis
    lines.append("## TRAFFIC & ENGAGEMENT")
    lines.append(f"Organic Users: {_val(k.organic_users)} ({_val(k.organic_users_change)})")
    lines.append(f"Engaged Sessions: {_val(k.engaged_sessions)} ({_val(k.engaged_sessions_change)})")
    lines.append(f"Avg Engagement: {_val(k.avg_engagement_time)}")
    lines.append(f"GSC Clicks: {_val(k.clicks)} ({_val(k.clicks_change)})")
    lines.append(f"GSC Impressions: {_val(k.impressions)} ({_val(k.impressions_change)})")
    if k.monthly_traffic:
        monthly = ", ".join(f"{tp.month}: {_val(tp.users)}" for tp in k.monthly_traffic)
        lines.append(f"Monthly Trend: {monthly}")
    lines.append("")

    # ── CWV ──
    c = facts.cwv
    lines.append("## CORE WEB VITALS")
    lines.append(f"Mobile Score: {_val(c.mobile_score)}/100")
    lines.append(f"Desktop Score: {_val(c.desktop_score)}/100")
    lines.append(f"LCP: {_val(c.lcp_seconds)}s")
    lines.append(f"INP: {_val(c.inp_ms)}ms")
    lines.append(f"CLS: {_val(c.cls_score)}")
    lines.append("")

    # ── Technical ──
    t = facts.technical
    lines.append("## TECHNICAL SEO")
    lines.append(f"Health Score: {_val(t.health_score)}")
    lines.append(f"Pages Audited: {_val(t.pages_audited)}")
    lines.append(f"Missing H1: {_val(t.missing_h1)}")
    lines.append(f"Missing Meta: {_val(t.missing_meta)}")
    lines.append(f"Missing Alt: {_val(t.missing_alt)}")
    lines.append(f"Thin Pages: {_val(t.thin_pages)}")
    if t.issues_list:
        lines.append(f"Issues ({len(t.issues_list)}):")
        for iss in t.issues_list[:8]:
            lines.append(f"  - [{iss.severity}] {iss.issue_text[:70]} ({iss.page})")
    lines.append("")

    # ── AI Overview ──
    aio_present = sum(1 for r in ranks if hasattr(r, "ai_overview") and r.ai_overview.is_available and str(r.ai_overview.value).lower() in ("yes", "true", "present", "1"))
    aio_total = sum(1 for r in ranks if hasattr(r, "ai_overview") and r.ai_overview.is_available)
    if aio_total > 0:
        lines.append("## AI OVERVIEWS")
        lines.append(f"AI Overview Present: {aio_present}/{aio_total} tracked keywords")
        lines.append("")

    # ── Action Plan ──
    if facts.action_plan:
        lines.append("## ACTION PLAN")
        for a in facts.action_plan[:12]:
            lines.append(f"  - [{a.priority}] ({a.team}) {a.task[:60]} — {a.owner}, ETA: {a.eta}")
        lines.append("")

    return "\n".join(lines)


def build_report_prompt(facts: ReportFacts, executive_narrative: str = "") -> str:
    """Build the full LLM prompt for report generation."""
    data_section = _build_data_section(facts)
    m = facts.metadata

    # Build verified client context
    from report.client_context import build_context_prompt_section
    client_context = build_context_prompt_section(m.client_name or "")

    prompt = f"""You are a senior SEO strategist at a top digital marketing agency. Write a professional, executive-ready monthly SEO report for {m.client_name or "the client"} covering {m.report_month or "this period"}.

## CRITICAL RULES — READ CAREFULLY
1. **NEVER invent or assume metrics that are not in the RAW DATA below.** If GSC clicks, impressions, GA4 users, engagement time, or similar traffic data shows "—" (not available), do NOT mention those metrics. Simply skip that topic.
2. **Only write about what the data actually contains.** If traffic/analytics data is entirely unavailable, focus the report on keyword rankings, Core Web Vitals, and technical SEO — the data that IS available.
3. **Every specific number must trace back to the RAW DATA.** No made-up percentages, no assumed trends, no invented year-over-year comparisons.
4. **Do not say "data is not yet available" in the report output** — instead, just omit sections where data is unavailable. The client sees only sections with real data.
5. **Never reference Google Search Console, GA4, or any analytics platform** unless the data explicitly came from that source (shown in the RAW DATA).

## CLIENT CONTEXT (for understanding who the client is — NOT for inventing data)
{client_context}

## STYLE GUIDELINES
- Write in a confident, consultative tone — like a senior agency partner briefing a client executive
- Use clear, business-focused language. Avoid excessive jargon.
- Include specific keyword examples and numbers from the data.
- Structure the report with clear sections and actionable takeaways.
- End with a summary of key priorities for the next period.

## STRUCTURE
Write a report with ONLY the sections where data is actually available. Use ## for section headers.

1. **Executive Summary** — 2-3 paragraph overview. Highlight the biggest win, key concern, and overall trajectory.

2. **Search Visibility & Keyword Performance** — Review ranking distribution, winners (keywords that gained), and areas needing attention (keywords that dropped). Include position distribution context.

3. **Core Web Vitals & Page Experience** (only if CWV data present) — Analyze mobile vs desktop performance, LCP/INP/CLS metrics.

4. **Technical SEO Health** (only if technical data present) — Review site health score, issues found, and recommendations.

5. **Strategic Recommendations** — Top 3-5 prioritized actions the client should take next month, organized by team (SEO, Dev, Content).

## RAW DATA (only what was provided — do not add more):
{data_section}

## ADDITIONAL CONTEXT
{executive_narrative or "No additional context provided."}

---
Write the complete report now. Use professional formatting. Make it compelling and insight-rich — this goes to the client's executive team."""
    return prompt


def generate_markdown_report(facts: ReportFacts, groq_client, executive_narrative: str = "") -> str:
    """Generate a full markdown SEO report via LLM."""
    prompt = build_report_prompt(facts, executive_narrative)
    logger.info(f"LLM prompt: {len(prompt)} chars")

    result = groq_client.chat(
        prompt=prompt,
        system_prompt="You are a senior SEO strategist writing an executive report. Write in markdown.",
        max_tokens=4096,
        temperature=0.4,
    )

    if not result:
        logger.warning("LLM returned no result; building fallback report")
        result = _build_fallback_report(facts, executive_narrative)

    return result


def _build_fallback_report(facts: ReportFacts, narrative: str = "") -> str:
    """Fallback report if LLM call fails — data-driven markdown."""
    m = facts.metadata
    lines = []
    lines.append(f"# Monthly SEO Report: {m.client_name or 'Client'}")
    lines.append(f"**Period:** {m.report_month or 'N/A'}  |  **Prepared by:** {m.agency_name or 'SEO Agency'}")
    lines.append("")

    if narrative:
        lines.append("## Executive Summary")
        lines.append(narrative)
        lines.append("")

    ranks = facts.rankings
    if ranks:
        lines.append(f"## Keyword Performance ({len(ranks)} tracked)")
        improved = [r for r in ranks if hasattr(r.change, 'is_available') and r.change.is_available and str(r.change.value).lstrip('+').lstrip('-').isdigit() and int(str(r.change.value)) > 0]
        dropped = [r for r in ranks if hasattr(r.change, 'is_available') and r.change.is_available and str(r.change.value).lstrip('+').lstrip('-').isdigit() and int(str(r.change.value)) < 0]
        if improved:
            lines.append(f"**Gaining:** {len(improved)} keywords improved this period.")
        if dropped:
            lines.append(f"**Dropped:** {len(dropped)} keywords lost position.")
        lines.append("")
        lines.append("| Keyword | Position | Change |")
        lines.append("|---------|----------|--------|")
        for r in ranks[:15]:
            lines.append(f"| {r.keyword[:40]} | {_val(r.position)} | {_change_str(r.change)} |")
        lines.append("")

    k = facts.kpis
    kpi_lines = []
    if _val(k.organic_users) != "—":
        kpi_lines.append(f"- Organic Users: {_val(k.organic_users)} ({_val(k.organic_users_change)})")
    if _val(k.clicks) != "—":
        kpi_lines.append(f"- GSC Clicks: {_val(k.clicks)} ({_val(k.clicks_change)})")
    if _val(k.impressions) != "—":
        kpi_lines.append(f"- GSC Impressions: {_val(k.impressions)} ({_val(k.impressions_change)})")
    if kpi_lines:
        lines.append("## Traffic Overview")
        lines.extend(kpi_lines)
        lines.append("")

    c = facts.cwv
    lines.append("## Core Web Vitals")
    lines.append(f"- Mobile Score: {_val(c.mobile_score)}/100")
    lines.append(f"- Desktop Score: {_val(c.desktop_score)}/100")
    if _val(c.lcp_seconds) != "—":
        lines.append(f"- LCP: {_val(c.lcp_seconds)}s {'(needs improvement)' if float(_val(c.lcp_seconds)) > 2.5 else '(healthy)'}")
    lines.append("")

    t = facts.technical
    lines.append("## Technical Health")
    lines.append(f"- Health Score: {_val(t.health_score)}")
    lines.append(f"- Total Issues: {_val(t.total_issues)}")
    lines.append("")

    if facts.action_plan:
        lines.append("## Recommended Actions")
        for a in facts.action_plan[:8]:
            lines.append(f"- **[{a.priority}]** ({a.team}) {a.task[:60]} — {a.owner}, ETA: {a.eta}")
        lines.append("")

    return "\n".join(lines)


def markdown_to_html(md: str, title: str = "SEO Report") -> str:
    """Convert markdown to a styled HTML page."""
    import html as htmlmod

    lines = md.split("\n")
    html_lines = []
    in_table = False
    in_list = False

    for line in lines:
        stripped = line.strip()

        # Skip table separators
        if stripped.startswith("|---") or stripped.startswith("|---------|"):
            continue

        # Tables
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                html_lines.append('<table>')
                in_table = True
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # Detect header vs body row
            if html_lines[-1].startswith("<table>"):
                html_lines.append("  <thead><tr>" + "".join(f"<th>{htmlmod.escape(c)}</th>" for c in cells) + "</tr></thead>")
                html_lines.append("  <tbody>")
            else:
                html_lines.append("    <tr>" + "".join(f"<td>{htmlmod.escape(c)}</td>" for c in cells) + "</tr>")
            continue
        elif in_table:
            html_lines.append("  </tbody></table>")
            in_table = False

        # Headers
        if stripped.startswith("## "):
            html_lines.append(f"<h2>{htmlmod.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            html_lines.append(f"<h1>{htmlmod.escape(stripped[2:])}</h1>")
            continue

        # Bold
        if stripped.startswith("**") and stripped.endswith("**"):
            html_lines.append(f"<p><strong>{htmlmod.escape(stripped[2:-2])}</strong></p>")
            continue

        # Lists
        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{htmlmod.escape(stripped[2:])}</li>")
            continue
        elif in_list:
            html_lines.append("</ul>")
            in_list = False

        # Empty lines
        if not stripped:
            html_lines.append("")
            continue

        # Regular paragraphs
        html_lines.append(f"<p>{htmlmod.escape(stripped)}</p>")

    if in_table:
        html_lines.append("  </tbody></table>")
    if in_list:
        html_lines.append("</ul>")

    body = "\n".join(html_lines)

    css = """
    <style>
      body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1e293b; line-height: 1.7; background: #f8fafc; }
      h1 { color: #0f2747; border-bottom: 3px solid #2563eb; padding-bottom: 10px; font-size: 28px; }
      h2 { color: #0f2747; margin-top: 32px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; font-size: 20px; }
      table { width: 100%; border-collapse: collapse; margin: 16px 0; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
      th { background: #0f2747; color: white; padding: 10px 14px; text-align: left; font-size: 13px; font-weight: 600; }
      td { padding: 8px 14px; border-bottom: 1px solid #f1f5f9; font-size: 13px; }
      tr:last-child td { border-bottom: none; }
      tr:nth-child(even) td { background: #f8fafc; }
      p { margin: 8px 0; font-size: 14px; color: #334155; }
      ul { margin: 8px 0 16px 0; }
      li { margin: 4px 0; font-size: 14px; }
      strong { color: #0f2747; }
    </style>
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{htmlmod.escape(title)}</title>{css}</head>
<body>
{body}
</body>
</html>"""
