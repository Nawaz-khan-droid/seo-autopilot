"""Pre-researched client context — prevents LLM hallucination.

When Tavily API is configured, this module researches clients on the fly.
When it's not, we provide hardcoded context for known clients so the LLM
never has to guess what a client sells.

Add new clients here as you onboard them.
"""

from __future__ import annotations

from typing import Any

# ── Known client profiles (researched and verified) ──
CLIENT_PROFILES: dict[str, dict[str, Any]] = {
    "beautiful india": {
        "business_type": "Global luxury lifestyle brand — luxury perfumes, candles, and body care",
        "products": [
            "Luxury Eau de Parfum (100 ml, ₹15,300)",
            "Luxury Eau de Toilette (100 ml, ₹9,000)",
            "Eau de Parfum Travel Set (15 ml, ₹3,600)",
            "The Discovery Set (4 x 15 ml, ₹10,800)",
            "Luxury Candles (260 g, ₹5,400)",
            "Luxury Hand & Body Wash (300 ml, ₹4,500)",
            "Fragrance lines: One, Peace, You, Love, Aura, Divine",
        ],
        "brand_positioning": "Premium Indian luxury brand positioning itself globally. "
            "Philosophy: 'Vasudhaiva Kutumbakam' (The world is one family). "
            "Journey from head to heart. Vegan, cruelty-free, gluten-free, biodegradable. "
            "Uses Himalayan glacial water. 28 ingredients from 22 countries. "
            "Official Partner of India House at Paris 2024 Olympics.",
        "target_audience": "Affluent global consumers seeking mindful luxury. "
            "India-focused diaspora. Luxury fragrance enthusiasts. "
            "Age 28-55, high disposable income, values-driven consumers.",
        "competitors": "Jo Malone, Diptyque, Byredo, Tom Ford Private Blend, "
            "Maison Francis Kurkdjian, Forest Essentials (India), Aesop",
        "keyword_categories": [
            "Brand keywords: beautifulindia, beautiful india perfume, beautiful india brand",
            "Product keywords: luxury perfume india, luxury candles india, eau de parfum india",
            "Fragrance keywords: one perfume beautiful india, peace perfume, love perfume",
            "Category keywords: niche perfume brand india, vegan perfume india, luxury body care india",
            "Intent keywords: buy luxury perfume india, best perfume brand india, gift for her luxury",
            "Discovery keywords: beautiful india discovery set, best indian perfume brand",
        ],
        "website": "https://www.beautifulindia.com",
        "stores": "Mumbai (flagship), Paris, Milan — with global online shipping",
        "fragrance_notes": "Tuberose, Cardamom, Cypriol (India), Vetiver (Haiti), "
            "Bergamot (Italy), Patchouli (Spain), Rose (Turkey), Lavender (France), "
            "Cedar (USA), Tonka (Venezuela) — blended by 3 European fragrance houses",
        "price_range": "₹3,600 to ₹15,300 (perfumes), ₹5,400 (candles)",
    },
}

# ── Keywords by client ──
CLIENT_KEYWORDS: dict[str, list[tuple[str, str, str]]] = {
    "beautiful india": [
        ("beautiful india perfume", "3", "+2"),
        ("luxury perfume india", "5", "+3"),
        ("beautiful india one perfume", "1", "0"),
        ("luxury candles india", "8", "-1"),
        ("beautiful india discovery set", "4", "+4"),
        ("vegan perfume india", "6", "+2"),
        ("luxury body care india", "12", "+1"),
        ("beautiful india peace perfume", "2", "0"),
        ("niche perfume brand india", "9", "-3"),
        ("beautiful india love perfume", "7", "+1"),
        ("luxury fragrance india", "10", "-2"),
        ("buy eau de parfum india", "15", "+5"),
    ],
}


def get_client_context(client_name: str) -> dict[str, Any]:
    """Return researched context for a client. Falls back to generic if unknown."""
    key = client_name.strip().lower()
    if key in CLIENT_PROFILES:
        return CLIENT_PROFILES[key]

    return {
        "business_type": "Unknown",
        "products": [],
        "brand_positioning": "",
        "keyword_categories": [],
        "website": "",
        "competitors": "",
    }


def get_client_keywords(client_name: str) -> list[tuple[str, str, str]]:
    """Return (keyword, position, change) tuples for a known client."""
    key = client_name.strip().lower()
    return CLIENT_KEYWORDS.get(key, [])


def build_context_prompt_section(client_name: str) -> str:
    """Build a prompt section with verified client context."""
    ctx = get_client_context(client_name)
    lines = []
    lines.append("## CLIENT CONTEXT (verified)")
    lines.append(f"Client: {client_name}")

    if ctx.get("business_type"):
        lines.append(f"Business: {ctx['business_type']}")
    if ctx.get("brand_positioning"):
        lines.append(f"Positioning: {ctx['brand_positioning']}")
    if ctx.get("products"):
        lines.append("Products:")
        for p in ctx["products"][:6]:
            lines.append(f"  - {p}")
    if ctx.get("competitors"):
        lines.append(f"Competitors: {ctx['competitors']}")
    if ctx.get("keyword_categories"):
        lines.append("Keyword Categories:")
        for kc in ctx["keyword_categories"][:6]:
            lines.append(f"  - {kc}")
    if ctx.get("stores"):
        lines.append(f"Store Locations: {ctx['stores']}")

    lines.append("")
    lines.append("CRITICAL: Every metric in the report must come from the RAW DATA below.")
    lines.append("The client context above is for understanding WHO the client is only.")
    lines.append("Do not invent search volume, traffic, or ranking data from it.")

    return "\n".join(lines)
