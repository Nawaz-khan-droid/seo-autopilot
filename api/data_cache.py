"""JSON data cache — bridges main.py pipeline sheets data to the API.

main.py writes sheet data to JSON after data collection.
api/main.py reads from JSON when Google Sheets aren't available directly.
This eliminates all hardcoded sample data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / "output" / "data_cache"
METADATA_FILE = CACHE_DIR / "_metadata.json"


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def save_sheet_data(
    client_name: str,
    report_month: str,
    tabs: dict[str, list[dict[str, Any]]],
) -> None:
    """Persist raw sheet data to JSON cache.

    Each tab becomes a separate JSON file. Metadata tracks the snapshot.
    Overwrites previous cache — only the latest run matters.
    """
    _ensure_dir()
    timestamp = datetime.now().isoformat(timespec="seconds")

    for tab_name, records in tabs.items():
        safe_name = tab_name.replace(" ", "_").lower()
        filepath = CACHE_DIR / f"{safe_name}.json"
        filepath.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")

    metadata = {
        "client_name": client_name,
        "report_month": report_month,
        "cached_at": timestamp,
        "tabs": list(tabs.keys()),
    }
    METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Data cache saved: %d tabs for %s %s", len(tabs), client_name, report_month)


def load_sheet_data() -> dict[str, list[dict[str, Any]]]:
    """Load all cached sheet data. Returns empty dict if no cache exists."""
    _ensure_dir()
    if not METADATA_FILE.exists():
        logger.warning("No data cache found at %s", METADATA_FILE)
        return {}

    try:
        metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Corrupt cache metadata: %s", e)
        return {}

    tabs = metadata.get("tabs", [])
    result: dict[str, list[dict[str, Any]]] = {}
    for tab_name in tabs:
        safe_name = tab_name.replace(" ", "_").lower()
        filepath = CACHE_DIR / f"{safe_name}.json"
        if filepath.exists():
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                result[tab_name] = data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Corrupt cache file %s: %s", filepath.name, e)

    logger.info("Data cache loaded: %d tabs from %s", len(result), metadata.get("cached_at", "unknown"))
    return result


def get_cache_metadata() -> dict[str, Any] | None:
    """Return cache metadata dict, or None if no cache."""
    _ensure_dir()
    if not METADATA_FILE.exists():
        return None
    try:
        return json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_audit_results(
    url: str,
    month: str,
    metrics: dict[str, Any],
    issues: list[dict[str, Any]] | None = None,
    rankings: list[dict[str, Any]] | None = None,
) -> None:
    """Bridge function: write audit results to data cache so report endpoint can read them.

    Converts the audit pipeline output into the tab-based format that
    _load_raw_data() → _build_facts() expects.
    """
    _ensure_dir()
    timestamp = datetime.now().isoformat(timespec="seconds")

    # Technical audit tab
    audit_tab = [{
        "URL": url,
        "Health Score": str(metrics.get("health_score", "")),
        "Pages Audited": str(metrics.get("pages_audited", 1)),
        "Missing H1": str(metrics.get("missing_h1_count", 0)),
        "Missing Meta": str(metrics.get("missing_meta_tags", 0)),
        "Missing Alt Tags": str(metrics.get("missing_alt_tags", 0)),
        "Total Images": str(metrics.get("total_images_found", 0)),
        "Thin Pages": str(metrics.get("thin_pages_detected", 0)),
        "Title": metrics.get("title", ""),
        "Meta Description": metrics.get("meta_description", ""),
        "Word Count": str(metrics.get("word_count", 0)),
        "Has Schema": "Yes" if metrics.get("has_yoast_schema") else "No",
        "Has OG Tags": "Yes" if metrics.get("has_og_tags") else "No",
    }]

    # Keywords / Rankings tab
    keywords_tab = []
    rankings_tab = []
    kw_list = rankings or []
    for kw_data in kw_list:
        kw = kw_data.get("keyword", "")
        pos = kw_data.get("position", "")
        if kw:
            keywords_tab.append({
                "Keyword": kw,
                "Position": str(pos) if pos else "Not Found",
                "Target URL": url,
            })
            rankings_tab.append({
                "Keyword": kw,
                "Position": str(pos) if pos else "Not Found",
                "Target URL": url,
                "Timestamp": timestamp,
            })

    # Issues tab
    issues_tab = issues or []

    tabs = {
        "Site Audit": audit_tab,
        "Keywords": keywords_tab,
        "SERP Snapshot": rankings_tab,
        "Website Tracking & Insights": [],
        "AI Analysis": [],
        "SERP History": [],
        "Monthly SEO Plan": [],
        "Competitor Snapshot": [],
    }

    for tab_name, records in tabs.items():
        safe_name = tab_name.replace(" ", "_").lower()
        filepath = CACHE_DIR / f"{safe_name}.json"
        filepath.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")

    metadata = {
        "client_name": url,
        "report_month": month,
        "cached_at": timestamp,
        "source": "audit_pipeline",
        "tabs": ["Site Audit", "Keywords", "SERP Snapshot"],
    }
    METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Audit results cached: %d tabs for %s %s", len(tabs), url, month)


def cleanup_old_reports(output_dir: str | Path, keep_per_type: int = 10) -> int:
    """Remove oldest report files per type, keeping only the latest N.

    Report types: *_Report_*.docx, *_Action_Plan_*.docx
    Returns the number of files deleted.
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return 0

    deleted = 0
    for pattern in ("*_Report_*.docx", "*_Action_Plan_*.docx"):
        files = sorted(output_path.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files[keep_per_type:]:
            try:
                f.unlink()
                deleted += 1
                logger.info("Cleaned up old report: %s", f.name)
            except OSError as e:
                logger.warning("Could not delete %s: %s", f.name, e)
    if deleted:
        logger.info("Cleanup: removed %d old report(s), keeping %d per type", deleted, keep_per_type)
    return deleted
