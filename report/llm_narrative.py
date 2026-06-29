from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from report.evidence import Evidence

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "openai/gpt-oss-120b"
FALLBACK_TIMEOUT_S = 60
_MAX_INPUT_CHARS = 7000  # ~1750 tokens, well under 8k context

# Phrases the LLM is known to hallucinate when no supporting data exists
HALLUCINATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"gmb", re.I), "GMB/local presence"),
    (re.compile(r"google (my )?business", re.I), "Google Business Profile"),
    (re.compile(r"local presence", re.I), "local presence"),
    (re.compile(r"trending (upward|downward)", re.I), "trend direction"),
    (re.compile(r"keyword.*trend", re.I), "keyword trends"),
    (re.compile(r"shopping (campaign|trend|behavior)", re.I), "shopping data"),
    (re.compile(r"backlink.*(grow|improv|increas)", re.I), "backlink growth trend"),
    (re.compile(r"traffic (grew|increased|declined|dropped)", re.I), "traffic change"),
]


def _strip_empty_data(data: dict[str, Any]) -> dict[str, Any]:
    """Remove fields whose values are Evidence.is_available==False, empty, or None.

    Prevents LLM from seeing empty/missing-data fields and hallucinating content
    around them (e.g., 'GMB local presence is growing' when no GMB data exists).
    """
    result: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, Evidence):
            if v.is_available:
                result[k] = v.value
        elif isinstance(v, dict):
            cleaned = _strip_empty_data(v)
            if cleaned:
                result[k] = cleaned
        elif isinstance(v, list):
            if len(v) > 0:
                result[k] = v
        elif v is not None and v != "" and v != "N/A":
            result[k] = v
    return result


def _verify_narrative(narrative: str, data_summary: str) -> list[str]:
    """Check generated narrative for hallucinated claims not supported by data.

    Returns list of detected hallucination warnings (empty list = clean).
    """
    warnings: list[str] = []
    data_lower = data_summary.lower()
    for pattern, label in HALLUCINATION_PATTERNS:
        if pattern.search(narrative) and not pattern.search(data_lower):
            warnings.append(f"Hallucinated '{label}' — no matching data in input")
    return warnings


def _groq_client() -> Groq | None:
    load_dotenv(override=True)
    key = os.environ.get("GROQ_API_KEY", "")
    return Groq(api_key=key) if key else None


def _call_groq(
    client: Groq,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.4,
) -> str | None:
    """Call Groq via SDK. Returns text content or None on failure.

    Falls back to FALLBACK_MODEL on first failure.
    """
    models_to_try = [model, FALLBACK_MODEL] if model != FALLBACK_MODEL else [model]

    for m in models_to_try:
        try:
            resp = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=FALLBACK_TIMEOUT_S,
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                logger.info("Groq narrative: model=%s chars=%d", m, len(content))
                return content.strip()
            logger.warning("Groq returned empty content for model=%s", m)
        except Exception as e:
            logger.warning("Groq model=%s failed: %s — trying fallback", m, e)

    return None


def _truncate_data_to_budget(data_json: str, max_chars: int = _MAX_INPUT_CHARS) -> str:
    """Truncate data JSON if it exceeds the token budget."""
    if len(data_json) <= max_chars:
        return data_json
    logger.warning("Narrative data %d chars exceeds budget %d — truncating", len(data_json), max_chars)
    return data_json[:max_chars] + '\n  "_truncated": true\n}'


def generate_executive_narrative(
    context_prompt: str,
    report_data: dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate a 3-paragraph executive narrative for the client report.

    Args:
        context_prompt: Client memory context (from client_memory.build_context_prompt)
        report_data: Dict with key metrics (rankings, traffic, technical, CWV)
        model: Groq model name

    Returns:
        Narrative string (3 paragraphs, ~300-500 words)
    """
    client = _groq_client()
    if not client:
        logger.warning("Groq not configured — skipping narrative")
        return ""

    cleaned_data = _strip_empty_data(report_data)
    data_json = json.dumps(cleaned_data, indent=2, default=str) if cleaned_data else "NO DATA AVAILABLE"
    data_json = _truncate_data_to_budget(data_json)

    system = (
        "You are a Senior Digital Marketing Agency Executive writing a monthly SEO report "
        "for a client. Write in clear, jargon-free language. Keep sentences under 15 words. "
        "Be direct and factual. Use the client context below to understand the business, "
        "but ONLY reference data from the metrics provided — never invent numbers.\n\n"
        "CRITICAL RULE: If a category (GMB, local presence, keyword trends, backlink trends, "
        "shopping data, traffic changes) has NO data in the provided JSON, do NOT mention it. "
        "Stick strictly to what is present. Do not fabricate trends, growth, or comparisons.\n\n"
        "ANTI-BOILERPLATE RULES:\n"
        "- Every sentence must reference a specific number or data point from the JSON.\n"
        "- Never write vague praise like 'strong performance' or 'solid results'. Use exact metrics.\n"
        "- Never write generic advice like 'continue optimizing'. Name the specific metric and target.\n"
        "- If you have fewer than 3 data points, write 1 paragraph, not 3. Never pad.\n"
        "- Never write 'there are' or 'it is important to' — start each sentence with the data.\n\n"
        f"{context_prompt}"
    )

    user = (
        "Write an executive summary based on this month's data (only data points present in the JSON below):\n\n"
        f"{data_json}\n\n"
        "Rules: Every sentence must cite a number. No padding paragraphs. "
        "If only 1 data category has values, write 1 sentence about it and nothing more. "
        "Order: metrics that improved first, metrics that declined second, "
        "then 1-2 specific recommended actions with numeric targets."
    )

    narrative = _call_groq(client, model, system, user, max_tokens=2048, temperature=0.4) or ""

    if narrative:
        warnings = _verify_narrative(narrative, data_json)
        if warnings:
            logger.warning("Narrative hallucination detected: %s", "; ".join(warnings))

    return narrative


def generate_action_plan_narrative(
    context_prompt: str,
    action_items: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate a strategic overview paragraph for the action plan.

    Args:
        context_prompt: Client memory context
        action_items: List of {team, task, priority, impact, effort, eta}
        model: Groq model name

    Returns:
        Narrative string (1-2 paragraphs)
    """
    client = _groq_client()
    if not client:
        logger.warning("Groq not configured — skipping narrative")
        return ""

    cleaned = [it for it in action_items if it.get("task")]

    system = (
        "You are a Lead Tech SEO Architect writing an internal action plan for the engineering team. "
        "Be specific and technical. Use the client context to frame priorities correctly.\n\n"
        "CRITICAL RULE: Only reference data points explicitly present in the action items below. "
        "Do not invent metrics, timelines, or dependencies.\n\n"
        f"{context_prompt}"
    )

    user = (
        "Summarize the strategic direction for next month's SEO work based on these action items:\n\n"
        f"{json.dumps(cleaned, indent=2, default=str) if cleaned else 'No action items provided.'}\n\n"
        "Write 1-2 paragraphs explaining the priority theme, quick wins vs long-term investments, "
        "and any dependencies the team should be aware of."
    )

    narrative = _call_groq(client, model, system, user, max_tokens=1024, temperature=0.3) or ""

    if narrative:
        warnings = _verify_narrative(narrative, json.dumps(cleaned, default=str))
        if warnings:
            logger.warning("Action plan narrative hallucination: %s", "; ".join(warnings))

    return narrative


def generate_audit_summary(
    context_prompt: str,
    audit_data: dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate a technical audit summary for the SEO Audit deliverable.

    Args:
        context_prompt: Client memory context
        audit_data: Dict with crawl results, issues, health score, page stats
        model: Groq model name

    Returns:
        Technical narrative string (2-3 paragraphs)
    """
    client = _groq_client()
    if not client:
        logger.warning("Groq not configured — skipping narrative")
        return ""

    cleaned_data = _strip_empty_data(audit_data)
    data_json = json.dumps(cleaned_data, indent=2, default=str) if cleaned_data else "NO DATA AVAILABLE"
    data_json = _truncate_data_to_budget(data_json)

    system = (
        "You are an elite Technical SEO Auditor. Analyze the crawl data strictly through the lens "
        "of this client's business profile. Focus on actionable technical gaps.\n\n"
        "CRITICAL RULE: Only reference metrics that are present in the data below. "
        "Do not mention GMB, local presence, keyword trends, traffic, or any other category "
        "not represented in the provided audit data.\n\n"
        "ANTI-BOILERPLATE RULES:\n"
        "- Every sentence must name a specific page, URL, or metric value from the JSON.\n"
        "- No general statements like 'there are technical issues to address' — say exactly how many and which.\n"
        "- No padding — if only 1 finding exists, write 1 sentence. Never add fluff.\n"
        "- Each recommended fix must mention the specific page or metric it targets.\n\n"
        f"{context_prompt}"
    )

    user = (
        "Analyze this SEO audit data:\n\n"
        f"{data_json}\n\n"
        "Rules: cite exact numbers from the data. 1 sentence per finding. "
        "Even 1 finding is enough — do not pad. "
        "Cover only what is present: specific page issues, status codes, missing elements."
    )

    narrative = _call_groq(client, model, system, user, max_tokens=2048, temperature=0.3) or ""

    if narrative:
        warnings = _verify_narrative(narrative, data_json)
        if warnings:
            logger.warning("Audit summary hallucination detected: %s", "; ".join(warnings))

    return narrative
