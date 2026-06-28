"""LLM-driven action plan generator.

Uses the ``seo_action_planner_skill.md`` as a reference knowledge framework,
combined with a procedural system prompt (instructions) in code. The two
are kept separate — the skill defines *what* the agent knows about SEO, the
instructions define *how* to produce the deliverable.

Pipeline:
  1. Serialise ``ReportFacts`` → structured JSON (omitting empty Evidence)
  2. Build system prompt = instructions (code) + skill reference (file)
  3. Call OpenRouter GPT 120B (fallback → Groq → deterministic generator)
  4. Parse & validate JSON response
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from report.facts import ActionItem, ReportFacts

logger = logging.getLogger(__name__)

SKILL_PATH = Path(__file__).resolve().parent / "seo_action_planner_skill.md"
DEFAULT_MODEL = "openai/gpt-oss-120b"        # GPT 120B on OpenRouter
FALLBACK_MODEL = "llama-3.3-70b-versatile"   # Groq fallback
MAX_TOKENS = 4096
TEMPERATURE = 0.3


# ---------------------------------------------------------------------------
# 1. Build system prompt (instructions) + load skill (knowledge)
# ---------------------------------------------------------------------------

def _load_skill() -> str:
    """Read the SEO knowledge framework from the skill file.

    This is pure reference material — team definitions, priority thresholds,
    decision heuristics, anti-hallucination guardrails. No output formatting
    instructions live here.
    """
    try:
        return SKILL_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Skill file not found at %s — using built-in fallback", SKILL_PATH)
        return _builtin_skill()


def _builtin_skill() -> str:
    """Compact fallback skill when the markdown file is missing."""
    return (
        "# SEO Knowledge Framework (built-in fallback)\n\n"
        "Priority levels: P0 (this week), P1 (next sprint), P2 (this sprint), P3 (backlog).\n"
        "Teams: Dev (technical/CWV), Content (on-page/SEO copy), SEO (rankings/strategy), "
        "Local (GBP/reviews), Off-Page (backlinks/DA).\n\n"
        "Key thresholds:\n"
        "- LCP > 4.0s → P0, 2.5-4.0s → P1\n"
        "- Mobile PSI < 50 → P0, 50-80 → P1\n"
        "- Missing H1/meta/alt → P1\n"
        "- Dropped 5+ positions → P1 recovery\n"
        "- No GBP posts in 30d → P1\n"
        "- Review count < 10 → P1\n"
        "- DA stagnant → P2 digital PR\n\n"
        "Anti-hallucination: If a data field is absent/null/— do NOT reference its category. "
        "Each action must cite a concrete data point from the input."
    )


def _build_system_prompt() -> str:
    """Combine output instructions (in code) with the SEO skill (file-based).

    The two sections are clearly separated so the LLM can distinguish
    *how to output* from *what to know*.
    """
    skill_md = _load_skill()

    return (
        "## INSTRUCTIONS — Output Rules\n\n"
        "You are a Senior Technical SEO Lead. Your task is to produce a "
        "structured action plan from the client's monthly audit data.\n\n"
        "Return ONLY a valid JSON array. No preamble, no markdown fences, "
        "no explanations outside the JSON.\n\n"
        "Each object in the array must have these keys:\n"
        "  - team: one of Dev, Content, SEO, Local, Off-Page\n"
        "  - task: specific string referencing actual data values from the input\n"
        "  - priority: P0, P1, P2, or P3 (see Knowledge Framework below)\n"
        "  - impact: high, medium, or low\n"
        "  - effort: estimated hours/days (e.g. 2h, 1d, 1w, Ongoing)\n"
        "  - owner: role or person\n"
        "  - dependency: null or short description of blocker\n"
        "  - eta: This week, Next sprint, This month, Ongoing, or TBD\n"
        "  - success_metric: measurable outcome\n"
        "  - status: always \"todo\"\n\n"
        "Generate 5-15 action items. Fewer than 5 means gaps in coverage. "
        "More than 15 creates noise.\n\n"
        "Every task string must include at least one concrete number or "
        "data point from the input JSON (e.g. \"LCP is 3.8s\" not "
        "\"Improve site speed\").\n\n"
        "---\n\n"
        "## KNOWLEDGE FRAMEWORK — Use this to guide your decisions\n\n"
        f"{skill_md}"
    )


# ---------------------------------------------------------------------------
# 2. Serialize ReportFacts → dict (with Evidence unwrapped)
# ---------------------------------------------------------------------------

def _ev(v: Any) -> Any:
    """Unwrap an Evidence value, returning None if unavailable."""
    if v is None:
        return None
    if hasattr(v, "is_available"):
        if not v.is_available:
            return None
        val = v.value
    else:
        val = v
    return val if val not in (None, "N/A", "", "—") else None


def _serialize_facts(facts: ReportFacts) -> dict[str, Any]:
    """Convert *facts* to a plain JSON-serialisable dict, omitting empty fields."""
    data: dict[str, Any] = {}

    # Metadata
    if facts.metadata.client_name:
        data["client_name"] = facts.metadata.client_name
    if facts.metadata.report_month:
        data["report_month"] = facts.metadata.report_month

    # KPIs
    kpi_fields = {
        "organic_users": facts.kpis.organic_users,
        "organic_users_change": facts.kpis.organic_users_change,
        "sessions": facts.kpis.sessions,
        "engaged_sessions": facts.kpis.engaged_sessions,
        "engaged_sessions_change": facts.kpis.engaged_sessions_change,
        "avg_engagement_time": facts.kpis.avg_engagement_time,
        "clicks": facts.kpis.clicks,
        "clicks_change": facts.kpis.clicks_change,
        "impressions": facts.kpis.impressions,
        "impressions_change": facts.kpis.impressions_change,
    }
    kpi_clean = {k: _ev(v) for k, v in kpi_fields.items() if _ev(v) is not None}
    if facts.kpis.monthly_traffic:
        kpi_clean["monthly_traffic"] = [
            {"month": p.month, "users": _ev(p.users)}
            for p in facts.kpis.monthly_traffic if _ev(p.users) is not None
        ]
    if kpi_clean:
        data["kpis"] = kpi_clean

    # CWV
    cwv_fields = {
        "mobile_score": facts.cwv.mobile_score,
        "desktop_score": facts.cwv.desktop_score,
        "lcp_seconds": facts.cwv.lcp_seconds,
        "inp_ms": facts.cwv.inp_ms,
        "cls_score": facts.cwv.cls_score,
        "render_blocking_ms": facts.cwv.render_blocking_ms,
    }
    cwv_clean = {k: _ev(v) for k, v in cwv_fields.items() if _ev(v) is not None}
    if cwv_clean:
        data["cwv"] = cwv_clean

    # Rankings
    if facts.rankings:
        ranks = []
        for r in facts.rankings:
            rr: dict[str, Any] = {"keyword": r.keyword}
            pos = _ev(r.position)
            if pos is not None:
                rr["position"] = pos
            chg = _ev(r.change)
            if chg is not None:
                rr["change"] = chg
            if r.search_volume is not None:
                rr["search_volume"] = r.search_volume
            if r.competition:
                rr["competition"] = r.competition
            aio = _ev(r.ai_overview)
            if aio is not None:
                rr["ai_overview"] = aio
            paa = _ev(r.paa)
            if paa is not None:
                rr["paa"] = paa
            if r.target_url:
                rr["target_url"] = r.target_url
            ranks.append(rr)
        if ranks:
            data["rankings"] = ranks

    # Technical
    tech_fields = {
        "health_score": facts.technical.health_score,
        "pages_audited": facts.technical.pages_audited,
        "total_issues": facts.technical.total_issues,
        "missing_h1": facts.technical.missing_h1,
        "missing_meta": facts.technical.missing_meta,
        "missing_alt": facts.technical.missing_alt,
        "thin_pages": facts.technical.thin_pages,
        "has_https": facts.technical.has_https,
        "has_canonical": facts.technical.has_canonical,
        "has_schema": facts.technical.has_schema,
    }
    tech_clean = {k: _ev(v) for k, v in tech_fields.items() if _ev(v) is not None}
    if facts.technical.issues_list:
        tech_clean["issues_list"] = [
            {"page": iss.page, "issue_text": iss.issue_text, "severity": iss.severity}
            for iss in facts.technical.issues_list
        ]
    if tech_clean:
        data["technical"] = tech_clean

    # Local SEO
    local_fields = {
        "map_pack_presence": facts.local_seo.map_pack_presence,
        "nap_status": facts.local_seo.nap_status,
        "review_count": facts.local_seo.review_count,
        "avg_rating": facts.local_seo.avg_rating,
        "gmb_posts": facts.local_seo.gmb_posts,
        "gmb_photos": facts.local_seo.gmb_photos,
        "gmb_reviews_responded": facts.local_seo.gmb_reviews_responded,
    }
    local_clean = {k: _ev(v) for k, v in local_fields.items() if _ev(v) is not None}
    if facts.local_seo.gmb_observations:
        local_clean["observations"] = facts.local_seo.gmb_observations
    if facts.local_seo.next_steps:
        local_clean["next_steps"] = facts.local_seo.next_steps
    if local_clean:
        data["local_seo"] = local_clean

    # Backlinks
    bl_fields = {
        "total_backlinks": facts.backlinks.total_backlinks,
        "ref_domains": facts.backlinks.ref_domains,
        "dofollow_count": facts.backlinks.dofollow_count,
        "nofollow_count": facts.backlinks.nofollow_count,
        "edu_links": facts.backlinks.edu_links,
        "gov_links": facts.backlinks.gov_links,
    }
    bl_clean = {k: _ev(v) for k, v in bl_fields.items() if _ev(v) is not None}
    if facts.backlinks.top_backlinks:
        bl_clean["top_backlinks"] = [
            {"domain": bl.domain, "title": bl.title, "da_score": bl.da_score}
            for bl in facts.backlinks.top_backlinks[:5]
        ]
    if bl_clean:
        data["backlinks"] = bl_clean

    # Authority
    auth_fields = {
        "da_values": facts.authority.da_values,
        "dofollow_ratio": facts.authority.dofollow_ratio,
    }
    auth_clean = {k: _ev(v) for k, v in auth_fields.items() if _ev(v) is not None}
    if facts.authority.verified_links:
        auth_clean["verified_links_count"] = len(facts.authority.verified_links)
    if facts.authority.strategy_pivot:
        auth_clean["strategy_pivot"] = facts.authority.strategy_pivot
    if auth_clean:
        data["authority"] = auth_clean

    # Site info
    si_clean: dict[str, Any] = {}
    if facts.site_info.title_tag:
        si_clean["title_tag"] = facts.site_info.title_tag
    if facts.site_info.word_count:
        si_clean["word_count"] = facts.site_info.word_count
    if facts.site_info.h1_count:
        si_clean["h1_count"] = facts.site_info.h1_count
    if facts.site_info.tech_stack:
        si_clean["tech_stack"] = [
            {"name": t.name, "version": t.version, "category": t.category}
            for t in facts.site_info.tech_stack
        ]
    og = _ev(facts.site_info.has_og_tags)
    if og:
        si_clean["has_og_tags"] = og
    rt = _ev(facts.site_info.has_robots_txt)
    if rt:
        si_clean["has_robots_txt"] = rt
    sx = _ev(facts.site_info.has_sitemap_xml)
    if sx:
        si_clean["has_sitemap_xml"] = sx
    if si_clean:
        data["site_info"] = si_clean

    # UX issues
    if facts.ux_issues:
        data["ux_issues"] = [
            {"title": u.title, "problem": u.problem, "fix": u.fix, "severity": u.severity}
            for u in facts.ux_issues
        ]

    # Activities, press, bookmarks
    if facts.seo_activities_completed:
        data["seo_activities_completed"] = facts.seo_activities_completed
    if facts.press_coverages:
        data["press_coverages"] = facts.press_coverages
    if facts.social_bookmarks:
        data["social_bookmarks"] = [{"title": s[0], "url": s[1], "site": s[2]} for s in facts.social_bookmarks]
    if facts.image_submissions:
        data["image_submissions"] = [{"title": s[0], "url": s[1], "site": s[2]} for s in facts.image_submissions]
    if facts.video_submissions:
        data["video_submissions"] = [{"title": s[0], "url": s[1], "site": s[2]} for s in facts.video_submissions]

    return data


# ---------------------------------------------------------------------------
# 3. LLM calls (OpenRouter → Groq fallback)
# ---------------------------------------------------------------------------

def _call_openrouter(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
) -> str | None:
    import requests

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.info("OpenRouter: no API key configured — skipping")
        return None

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        logger.info("OpenRouter (%s): %d chars received", model, len(content))
        return content
    except Exception as e:
        logger.warning("OpenRouter call failed: %s", e)
        return None


def _call_groq(
    system_prompt: str,
    user_prompt: str,
    model: str = FALLBACK_MODEL,
    max_tokens: int = MAX_TOKENS,
    temperature: float = TEMPERATURE,
) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        logger.info("Groq: no API key configured — skipping")
        return None

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=60,
        )
        content = resp.choices[0].message.content
        if content and content.strip():
            logger.info("Groq (%s): %d chars received", model, len(content))
            return content.strip()
    except Exception as e:
        logger.warning("Groq call failed: %s", e)
    return None


# ---------------------------------------------------------------------------
# 4. Parse LLM response → list[ActionItem]
# ---------------------------------------------------------------------------

_TEAMS = frozenset({"Dev", "Content", "SEO", "Local", "Off-Page"})
_PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})
_IMPACTS = frozenset({"high", "medium", "low"})
_STATUSES = frozenset({"todo", "in_progress", "done", "blocked", "cancelled"})


def _extract_json(text: str) -> str | None:
    """Extract a JSON array from arbitrary text (strip markdown fences)."""
    text = text.strip()
    # Remove ```json ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Trim non-JSON leading/trailing text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


def _parse_response(text: str) -> list[dict[str, Any]]:
    """Parse LLM response text into a list of action-item dicts."""
    raw = _extract_json(text)
    if not raw:
        logger.warning("LLM response contains no JSON array")
        return []

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("LLM response is not valid JSON: %s", e)
        return []

    if not isinstance(items, list):
        logger.warning("LLM response is not a JSON array")
        return []

    validated: list[dict[str, Any]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        task = str(item.get("task", "")).strip()
        if not task or len(task) < 10:
            continue
        team = str(item.get("team", "")).strip()
        if team not in _TEAMS:
            team = "SEO"
        priority = str(item.get("priority", "P2")).strip()
        if priority not in _PRIORITIES:
            priority = "P2"
        impact = str(item.get("impact", "medium")).strip().lower()
        if impact not in _IMPACTS:
            impact = "medium"
        validated.append({
            "team": team,
            "task": task,
            "priority": priority,
            "impact": impact,
            "effort": str(item.get("effort", "4h")).strip() or "4h",
            "owner": str(item.get("owner", "Unassigned")).strip() or "Unassigned",
            "dependency": item.get("dependency") if item.get("dependency") else None,
            "eta": str(item.get("eta", "TBD")).strip() or "TBD",
            "success_metric": str(item.get("success_metric", "")).strip(),
            "status": "todo",
        })

    logger.info("LLM action plan: %d items parsed from %d raw", len(validated), len(items))
    return validated


# ---------------------------------------------------------------------------
# 5. Main entry point
# ---------------------------------------------------------------------------

def generate_llm_action_plan(facts: ReportFacts) -> list[ActionItem]:
    """Generate action items using the LLM (GPT 120B) SEO skill.

    Falls back to the deterministic ``action_plan_generator.generate_action_plan``
    if the LLM is unavailable or returns invalid output.
    """
    # Serialize facts
    data = _serialize_facts(facts)
    if not data:
        logger.info("No audit data available — falling back to deterministic generator")
        return _fallback(facts)

    system_prompt = _build_system_prompt()
    user_prompt = (
        "Generate an SEO action plan for this client based on the following "
        "monthly audit data.\n\n"
        f"{json.dumps(data, indent=2, default=str)}\n\n"
        "Return ONLY a JSON array of action items."
    )

    # Try OpenRouter GPT 120B first
    logger.info("LLM action planner: calling OpenRouter GPT 120B")
    response = _call_openrouter(system_prompt, user_prompt)

    # Fallback to Groq
    if not response:
        logger.info("LLM action planner: falling back to Groq %s", FALLBACK_MODEL)
        response = _call_groq(system_prompt, user_prompt)

    # Parse
    if response:
        parsed = _parse_response(response)
        if parsed:
            items = [_dict_to_action_item(d) for d in parsed]
            logger.info("LLM action plan: %d items generated", len(items))
            return items

    # Final fallback
    logger.warning("LLM action planner failed — falling back to deterministic generator")
    return _fallback(facts)


def _dict_to_action_item(d: dict[str, Any]) -> ActionItem:
    return ActionItem(
        team=d.get("team", "SEO"),
        task=d.get("task", ""),
        priority=d.get("priority", "P2"),
        impact=d.get("impact", "medium"),
        effort=d.get("effort", "4h"),
        owner=d.get("owner", "Unassigned"),
        dependency=d.get("dependency"),
        eta=d.get("eta", "TBD"),
        success_metric=d.get("success_metric", ""),
        status=d.get("status", "todo"),
    )


def _fallback(facts: ReportFacts) -> list[ActionItem]:
    """Deterministic fallback — no LLM required."""
    try:
        from report.action_plan_generator import generate_action_plan
        items = generate_action_plan(facts)
        logger.info("Deterministic fallback: %d action items", len(items))
        return items
    except Exception as e:
        logger.error("Deterministic fallback also failed: %s", e)
        return []
