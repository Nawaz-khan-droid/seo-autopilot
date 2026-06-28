from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _groq_client() -> Groq | None:
    load_dotenv(override=True)
    key = os.environ.get("GROQ_API_KEY", "")
    return Groq(api_key=key) if key else None


def classify_niche(
    url: str,
    title: str,
    meta_description: str,
    h1_texts: list[str],
    body_snippet: str,
    tavily_guess: str,
) -> dict[str, Any]:
    """Classify a website's niche using multi-signal input and Groq LLM.

    Uses page title, meta, H1s, body content, and Tavily's rough guess to
    produce a verified niche classification. Falls back to Tavily guess
    on any failure (zero workflow disruption).

    Returns:
        {
            "verified_niche": str (e.g., "Fintech / Remittance"),
            "confidence_score": float (0.0-1.0),
            "category": str (e.g., "fintech"),
            "source": str ("groq_classifier" | "tavily_fallback" | "default"),
        }
    """
    client = _groq_client()
    if not client:
        logger.warning("Groq not available — using Tavily guess: %s", tavily_guess)
        return _fallback(tavily_guess, "groq_unavailable")

    h1_text = "; ".join(h1_texts[:3]) if h1_texts else "(no H1 found)"

    prompt = (
        "You are an SEO niche classifier. Analyze the signals below and classify the website. "
        "Respond STRICTLY in JSON with keys: verified_niche, confidence_score, category.\n\n"
        f"Target URL: {url}\n"
        f"Tavily Guess: {tavily_guess}\n"
        f"Page Title: {title}\n"
        f"Meta Description: {meta_description}\n"
        f"H1 Headers: {h1_text}\n"
        f"Content Snippet: {body_snippet[:300]}\n\n"
        "Rules:\n"
        "- verified_niche: precise classification like 'Fintech / Remittance', "
        "'E-Commerce / Luxury Goods', 'B2B SaaS', 'Local Service'\n"
        "- confidence_score: float 0.0-1.0 based on signal agreement\n"
        "- category: one word for baseline mapping: ecommerce | fintech | saas | local | general\n"
        "JSON only, no explanation."
    )

    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=300,
        )
        content = resp.choices[0].message.content
        if content:
            data = json.loads(content.strip())
            verified = data.get("verified_niche", "").strip()
            if verified:
                result = {
                    "verified_niche": verified,
                    "confidence_score": float(data.get("confidence_score", 0.7)),
                    "category": data.get("category", "general").lower().strip(),
                    "source": "groq_classifier",
                }
                logger.info(
                    "Niche classifier: %s → %s (cat=%s, conf=%.2f)",
                    url, verified, result["category"], result["confidence_score"],
                )
                return result

    except Exception as e:
        logger.warning("Niche classifier failed for %s: %s", url, e)

    return _fallback(tavily_guess, "classifier_failed")


def _fallback(tavily_guess: str, reason: str) -> dict[str, Any]:
    """Return best-guess niche when classifier can't run."""
    guess_lower = tavily_guess.lower()
    if "e-commerce" in guess_lower or "ecommerce" in guess_lower:
        category = "ecommerce"
    elif any(x in guess_lower for x in ["fintech", "financial", "remittance", "payment", "banking"]):
        category = "fintech"
    elif any(x in guess_lower for x in ["saas", "software", "b2b", "enterprise"]):
        category = "saas"
    elif any(x in guess_lower for x in ["local", "service", "restaurant", "clinic"]):
        category = "local"
    else:
        category = "general"

    return {
        "verified_niche": tavily_guess or "General",
        "confidence_score": 0.5,
        "category": category,
        "source": f"tavily_fallback_{reason}",
    }
