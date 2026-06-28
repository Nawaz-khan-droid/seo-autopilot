"""Multi-client sheet mapper — discovers tab structures dynamically.

Every client Google Sheet may have different tab names and column layouts.
This module introspects a sheet, classifies each tab by its header pattern,
and extracts records in a standardised format.

No hardcoded tab names. No hallucinated data. Every value comes from
one of the discovered tabs.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from gspread import Spreadsheet, Worksheet

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 4

# ── Header keyword signals for each data type ──
# (type_name, required_keywords, optional_keywords, disqualifying_keywords)
CLASSIFIERS: list[tuple[str, list[str], list[str], list[str]]] = [
    ("keywords",
     ["Keyword"],
     ["Target URL", "Location", "Device", "Search Intent", "Volume"],
     ["Position", "Run Date", "Ranking URL"]),
    ("serp_snapshot",
     ["Keyword", "Position"],
     ["Run Date", "Ranking URL", "Data Availability", "Device", "AI Overview", "Rank"],
     ["Timestamp"]),
    ("serp_history",
     ["Keyword", "Position", "Timestamp"],
     ["Run Date", "Ranking URL", "Device"],
     []),
    ("site_audit",
     ["URL"],
     ["H1", "Title", "Issues", "Word Count", "Meta Description", "Images Missing Alt", "LLM Summary"],
     []),
    ("website_insights",
     ["URL"],
     ["Mobile PSI", "Desktop PSI", "Clicks", "Impressions"],
     ["Keyword", "Position"]),
    ("action_plan",
     [],
     ["Details", "Task", "Item", "Priority", "Section", "Team", "ETA"],
     ["Position", "Ranking URL"]),
    ("ai_analysis",
     ["Keyword"],
     ["Observed Change", "Likely Cause", "Recommendation", "Priority"],
     ["Position"]),
    ("competitors",
     ["Competitor"],
     ["Domain", "DA", "Overlap"],
     []),
    ("backlinks",
     ["Domain"],
     ["DA", "Status", "Anchor", "Submitted Link"],
     []),
    ("onpage_seo",
     ["URL"],
     ["Title", "Meta Description", "H1", "H2"],
     []),
    ("alt_text",
     ["Alt text"],
     ["Image", "Img Address", "Target Keyword"],
     []),
    ("news_mentions",
     ["URL"],
     ["Title", "Meta Description"],
     ["Position"]),
    ("technical_audit",
     [],
     ["Error", "Status", "Robots", "Sitemap", "Score"],
     ["Keyword"]),
    ("redirects",
     ["Old URL"],
     ["Redirected", "New URL"],
     []),
]

TRANSPOSED_CLASSIFIERS: list[tuple[str, list[str], list[str]]] = [
    ("website_insights",
     ["Organic Users", "Sessions", "Traffic"],
     ["Page Views", "Bounce Rate"]),
]


def _normalise(s: str) -> str:
    return s.strip().lower().replace("\n", " ").replace("\u00a0", " ").replace("\ufe0f", "")


def _header_joined(headers: list[str]) -> str:
    return " ".join(_normalise(h) for h in headers)


def _score_tab(headers: list[str], required: list[str],
               optional: list[str], disqualify: list[str]) -> tuple[int, bool]:
    """Score a tab against a classifier.

    Returns (score, disqualified). Disqualified if any disqualifying keyword is present.
    """
    joined = _header_joined(headers)
    score = 0
    for kw in required:
        if _normalise(kw) in joined:
            score += 3
    for kw in optional:
        if _normalise(kw) in joined:
            score += 1
    for kw in disqualify:
        if _normalise(kw) in joined:
            return (0, True)
    return (score, False)


def _has_date_columns(headers: list[str]) -> bool:
    """True if headers contain date-like patterns (e.g. '25th December', '15 Jan', '2026-06-05')."""
    date_count = 0
    for h in headers:
        h_norm = _normalise(h)
        # Pattern: "25th December", "15 Jan", "1 March" etc.
        if re.search(r'\b\d+(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', h_norm):
            date_count += 1
        # Pattern: "2026-06-05" ISO date
        elif re.search(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', h_norm):
            date_count += 1
        # Pattern: "3 Feb", "15 Feb 2024"
        elif re.search(r'\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b', h_norm):
            date_count += 1
        # Pattern: "March 2026", "April 2026" (month names followed by year)
        elif re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b', h_norm):
            date_count += 1
    return date_count > 2


def _has_single_header_row(all_values: list[list[str]]) -> bool:
    """True if the tab has only a header row and no data rows."""
    return len(all_values) < 2 or all(
        not any(cell.strip() for cell in row)
        for row in all_values[1:]
    )


def _any_header_match(headers: list[str], keywords: list[str]) -> bool:
    """True if at least one header contains one of the keywords (case-insensitive)."""
    joined = _header_joined(headers)
    for kw in keywords:
        if _normalise(kw) in joined:
            return True
    return False


def classify_tab(ws: Worksheet) -> tuple[str, float, list[list[str]]] | None:
    """Classify a worksheet tab.

    Returns (data_type, confidence_score, all_values) or None if unclassifiable.
    """
    try:
        all_values = ws.get_all_values()
    except Exception as e:
        logger.warning("Cannot read tab '%s': %s", ws.title, e)
        return None

    if not all_values or len(all_values) < 2:
        return None

    headers = [str(h) for h in all_values[0] if str(h).strip()]

    if not headers or _has_single_header_row(all_values):
        return None

    has_dates = _has_date_columns(headers)

    # Special case: date-column SERP tabs
    # Scan first few data rows for a keyword in the first column
    first_keyword = ""
    for row in all_values[1:4]:
        if row and str(row[0]).strip():
            first_keyword = str(row[0]).strip()
            break

    if has_dates and _any_header_match(headers, ["Keyword"]):
        has_volume = _any_header_match(headers, ["Avg. monthly searches", "Volume", "Search Volume"])
        dtype = "serp_history" if has_volume else "serp_snapshot"
        logger.info("Tab '%s' classified as %s (date-column SERP)", ws.title, dtype)
        return (dtype, SCORE_THRESHOLD + 2, all_values)

    best_type: str | None = None
    best_score = 0

    for dtype, required, optional, disqualify in CLASSIFIERS:
        # Skip classifiers that don't match date-column tabs
        if has_dates and dtype in ("keywords", "action_plan", "site_audit", "competitors", "ai_analysis"):
            continue

        score, disq = _score_tab(headers, required, optional, disqualify)
        if disq:
            continue
        if score > best_score:
            best_score = score
            best_type = dtype

    # Try transposed classifiers
    if not has_dates:
        first_col = [
            str(row[0]).strip() for row in all_values[1:]
            if row and str(row[0]).strip()
        ]
        for dtype, required, optional in TRANSPOSED_CLASSIFIERS:
            score = 0
            for val in first_col:
                v_norm = _normalise(val)
                for kw in required:
                    if _normalise(kw) in v_norm:
                        score += 3
                for kw in optional:
                    if _normalise(kw) in v_norm:
                        score += 1
            if score > best_score:
                best_score = score
                best_type = dtype

    if best_type and best_score >= SCORE_THRESHOLD:
        logger.info("Tab '%s' classified as %s (score=%d)", ws.title, best_type, best_score)
        return (best_type, best_score, all_values)
    return None


# ═══════════════════════════════════════════════════════════════
# EXTRACTORS
# ═══════════════════════════════════════════════════════════════

def _extract_standard(headers: list[str], rows: list[list[str]]) -> list[dict[str, Any]]:
    """Extract records from a standard columnar tab."""
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        rec: dict[str, Any] = {}
        has_data = False
        for i, h in enumerate(headers):
            val = str(row[i]).strip() if i < len(row) else ""
            rec[h] = val
            if val:
                has_data = True
        if has_data:
            records.append(rec)
    return records


def _extract_transposed(headers: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract from transposed tab (metrics in rows, months in columns).

    Returns a dict like:
    {
        "months": ["March 2026", "April 2026"],
        "Organic Users": "423",
        "Sessions": "629",
        ...
    }
    """
    result: dict[str, Any] = {"_type": "transposed"}
    for row in rows:
        if not row or not row[0].strip():
            continue
        metric = row[0].strip()
        vals = {}
        for ci, col in enumerate(headers[1:], 1):
            if ci < len(row):
                vals[col] = row[ci].strip()
        result[metric] = vals
    result["months"] = headers[1:]
    return result


def _extract_serp_columns(headers: list[str], rows: list[list[str]]) -> list[dict[str, Any]]:
    """Extract from date-as-columns format (e.g. NEW SERP tab).

    Returns standardised SERP snapshot records.
    """
    records: list[dict[str, Any]] = []
    date_col_indices: list[int] = []
    kw_col = 0
    url_col = 1

    for i, h in enumerate(headers):
        h_norm = _normalise(h)
        if re.search(r'\d+(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', h_norm):
            date_col_indices.append(i)
        elif "url" in h_norm and "target" in h_norm:
            url_col = i

    for row in rows[1:]:
        if not row:
            continue
        keyword = str(row[kw_col]).strip() if kw_col < len(row) else ""
        if not keyword:
            continue
        target_url = str(row[url_col]).strip() if url_col < len(row) else ""

        for di in date_col_indices:
            if di >= len(row):
                continue
            pos = str(row[di]).strip()
            if not pos or pos.upper() in ("NA", "N/A", ""):
                continue
            date_label = headers[di].strip()
            records.append({
                "Keyword": keyword,
                "Target URL": target_url,
                "Position": pos,
                "Run Date": date_label,
                "Data Availability": "Found",
            })
    return records


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def discover(sheet: Spreadsheet) -> dict[str, list[dict[str, Any]]]:
    """Discover all tabs in a sheet and extract structured data.

    Returns a dict like:
    {
        "keywords": [{...}, ...],
        "serp_snapshot": [{...}, ...],
        ...
    }
    """
    results: dict[str, list[dict[str, Any]]] = {}

    for ws in sheet.worksheets():
        try:
            classification = classify_tab(ws)
            if classification is None:
                continue

            dtype, score, all_values = classification
            headers = [str(h) for h in all_values[0] if str(h).strip()]

            if dtype in ("serp_snapshot", "serp_history") and _has_date_columns(headers):
                records = _extract_serp_columns(headers, all_values)
            elif dtype == "website_insights" and all_values[0][0].strip().lower() not in ("url", "analysis"):
                records = [_extract_transposed(headers, all_values)]
            else:
                records = _extract_standard(headers, all_values)

            if records:
                results.setdefault(dtype, []).extend(records)
        except Exception as e:
            logger.warning("Error processing tab '%s': %s", ws.title, e)

    logger.info("Sheet discovery complete: %d data types", len(results))
    for dtype, recs in results.items():
        logger.info("  %s: %d records", dtype, len(recs))
    return results


def validate_data(data: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Validate discovered data and return warnings."""
    warnings: list[str] = []
    has_rankings = bool(data.get("serp_snapshot") or data.get("serp_history"))
    if not has_rankings:
        warnings.append("No ranking data (SERP Snapshot or History) found")
    has_kw = bool(data.get("keywords"))
    if not has_kw:
        warnings.append("No Keywords tab found — using deduped ranking keywords")
    for dtype, recs in data.items():
        if dtype == "serp_snapshot":
            empty = sum(1 for r in recs if not str(r.get("Position", "") or "").strip())
            if empty:
                warnings.append(f"SERP Snapshot: {empty}/{len(recs)} empty positions")
    return warnings
