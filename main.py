from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from config.serp_config import RANK_PROVIDERS
from config.settings import (
    APIFY_API_KEY,
    CREDENTIALS_PATH,
    GA4_PROPERTY_ID,
    GROQ_API_KEY,
    GROQ_MODEL,
    GSC_SITE_URL,
    MAX_KEYWORDS,
    OPENROUTER_API_KEY,
    PAGESPEED_API_KEY,
    SEARCHAPI_API_KEY,
    SERPAPI_KEY,
    SHEET_NAME,
)
from modules.apify_client import ApifyClient
from modules.browseros_client import BrowserOSClient
from modules.ga4_client import AnalyticsClient
from modules.groq_client import GroqClient
from modules.logger_config import setup_logging
from modules.openrouter_client import OpenRouterClient
from modules.pagespeed import PageSpeedClient
from modules.search_console import SearchConsoleClient
from modules.searchapi_client import SearchApiClient
from modules.serp_client import SerpClient
from modules.sheet_client import SheetClient
from orchestrator.ai_analysis import AiAnalysisWorkflow, _classify_search_intent_rule
from orchestrator.serp_snapshot import SerpSnapshotWorkflow
from orchestrator.site_audit import SiteAuditWorkflow
from orchestrator.website_insights import WebsiteInsightsWorkflow

logger = logging.getLogger(__name__)


def _init_gsc(credentials_path: str) -> SearchConsoleClient | None:
    if not GSC_SITE_URL:
        return None
    return SearchConsoleClient(
        credentials_path=credentials_path, site_url=GSC_SITE_URL
    )


def _init_analytics(credentials_path: str) -> AnalyticsClient | None:
    if not GA4_PROPERTY_ID:
        return None
    return AnalyticsClient(
        credentials_path=credentials_path, property_id=GA4_PROPERTY_ID
    )


def _load_keywords(sheet: SheetClient) -> list[dict[str, Any]]:
    """Read keywords ONCE at the start of the pipeline. Same snapshot
    is passed to every workflow, so adding keywords mid-run can't
    cause a mismatch.
    """
    try:
        ws = sheet.get_tab("Keywords")
        return ws.get_all_records()
    except Exception as e:
        logger.critical(f"Could not read Keywords tab: {e}")
        return []


def _populate_missing_search_intent(
    sheet: SheetClient, records: list[dict[str, Any]],
) -> int:
    """Rule-based intent classification. Writes ONLY to cells that are
    empty — never overwrites user-edited or previously classified
    values.

    Returns the number of cells updated.
    """
    try:
        ws = sheet.get_tab("Keywords")
    except Exception as e:
        logger.warning(f"Could not access Keywords tab for intent: {e}")
        return 0

    updates: list[dict[str, Any]] = []
    for row_idx, rec in enumerate(records, start=2):  # row 1 is header
        existing = str(rec.get("Search Intent", "") or "").strip()
        if existing:
            continue
        keyword = str(rec.get("Keyword", "") or "").strip()
        target_url = str(rec.get("Target URL", "") or "").strip()
        if not keyword or not target_url:
            continue
        intent = _classify_search_intent_rule(keyword, target_url)
        updates.append({"row": row_idx, "col": 5, "value": intent})

    applied = 0
    for upd in updates:
        try:
            ws.update_cell(upd["row"], upd["col"], upd["value"])
            applied += 1
        except Exception as e:
            logger.debug(f"Could not write intent at row {upd['row']}: {e}")
    if applied:
        logger.info(f"Populated {applied} missing Search Intent cells")
    return applied


def main() -> int:
    setup_logging()
    logger.info("=" * 60)
    logger.info("SEO Operations Autopilot — starting run")
    logger.info("=" * 60)

    try:
        sheet = SheetClient(
            credentials_path=CREDENTIALS_PATH, sheet_name=SHEET_NAME
        )
        serp = SerpClient(api_key=SERPAPI_KEY) if SERPAPI_KEY else None
        searchapi = (
            SearchApiClient(api_key=SEARCHAPI_API_KEY)
            if SEARCHAPI_API_KEY
            else None
        )
        browseros = BrowserOSClient()
        apify = (
            ApifyClient(api_key=APIFY_API_KEY) if APIFY_API_KEY else None
        )
        groq = GroqClient(api_key=GROQ_API_KEY, model=GROQ_MODEL)
        pagespeed = PageSpeedClient(
            api_key=PAGESPEED_API_KEY,
            credentials_path=CREDENTIALS_PATH,
        )
        gsc = _init_gsc(CREDENTIALS_PATH)
        analytics = _init_analytics(CREDENTIALS_PATH)
        openrouter = (
            OpenRouterClient(api_key=OPENROUTER_API_KEY)
            if OPENROUTER_API_KEY
            else None
        )

        logger.info("All clients initialized successfully")
        logger.info(
            f"Clients active: SERP=yes SearchApi={'yes' if searchapi else 'no'} "
            f"Apify={'yes' if apify else 'no'} "
            f"BrowserOS=yes "
            f"Groq=yes PageSpeed=yes "
            f"GSC={'yes' if gsc else 'no'} "
            f"GA4={'yes' if analytics else 'no'} "
            f"OpenRouter={'yes' if openrouter else 'no'}"
        )
        logger.info(f"Provider rank order: {RANK_PROVIDERS}")

    except Exception as e:
        logger.critical(f"Failed to initialize clients: {e}", exc_info=True)
        return 1

    # Read keywords ONCE at pipeline start. Same snapshot for all phases.
    keywords = _load_keywords(sheet)
    logger.info(f"Loaded {len(keywords)} keyword records from Keywords tab")

    # Intent classification — guard against overwriting existing values.
    _populate_missing_search_intent(sheet, keywords)

    try:
        logger.info("--- Phase 1: SERP Snapshot ---")
        serp_workflow = SerpSnapshotWorkflow(
            sheet=sheet, serp=serp, max_keywords=MAX_KEYWORDS,
            searchapi=searchapi, apify=apify, browseros=browseros,
            keywords=keywords, provider_order=list(RANK_PROVIDERS),
        )
        serp_workflow.run()
    except Exception as e:
        logger.error(f"SERP Snapshot phase failed: {e}", exc_info=True)

    try:
        logger.info("--- Phase 2: Website Insights ---")
        insights_workflow = WebsiteInsightsWorkflow(
            sheet=sheet,
            pagespeed=pagespeed,
            browseros=browseros,
            gsc=gsc,
            analytics=analytics,
        )
        insights_workflow.run(keywords=keywords)
    except Exception as e:
        logger.error(f"Website Insights phase failed: {e}", exc_info=True)

    try:
        logger.info("--- Phase 3: AI Analysis ---")
        analysis_workflow = AiAnalysisWorkflow(
            sheet=sheet, groq=groq, openrouter=openrouter,
            keywords=keywords,
        )
        analysis_workflow.run()
    except Exception as e:
        logger.error(f"AI Analysis phase failed: {e}", exc_info=True)

    try:
        logger.info("--- Phase 4: Site Audit (BrowserOS + LLM) ---")
        audit_workflow = SiteAuditWorkflow(
            sheet=sheet, groq=groq, browseros=browseros,
        )
        audit_workflow.run(keywords=keywords)
    except Exception as e:
        logger.error(f"Site Audit phase failed: {e}", exc_info=True)

    try:
        logger.info("--- Phase 5: Monthly SEO Plan ---")
        from orchestrator.monthly_seo_plan import MonthlySeoPlanWorkflow
        plan_workflow = MonthlySeoPlanWorkflow(
            sheet=sheet, groq=groq, browseros=browseros,
        )
        plan_workflow.run()
    except Exception as e:
        logger.error(f"Monthly SEO Plan phase failed: {e}", exc_info=True)

    # ── Phase 6: Report Generation (reads sheets → builds DOCX) ──
    try:
        logger.info("--- Phase 6: Report Generation ---")
        _run_report_phase(sheet, sheet_name=SHEET_NAME)
    except Exception as e:
        logger.error(f"Report Generation phase failed: {e}", exc_info=True)

    logger.info("=" * 60)
    logger.info("SEO Operations Autopilot — run complete")
    logger.info("=" * 60)
    return 0


def _get_tab_data(sheet, tab_name: str) -> list[dict]:
    """Safely read all records from a sheet tab. Returns empty list on failure."""
    try:
        return sheet.read_records(tab_name)
    except Exception as e:
        logger.warning(f"Could not read tab '{tab_name}': {e}")
        return []


def _run_report_phase(sheet, sheet_name: str) -> None:
    """Phase 6: read collected data from sheets, build facts, generate DOCX reports.

    Uses lazy imports to keep main.py import chain clean.
    Caches raw sheet data to JSON for API consumption.
    """
    from report.docx_action_plan import build_action_plan_docx
    from report.docx_report import build_clients_report
    from report.facts_loader import build_facts

    from api.data_cache import save_sheet_data

    TAB_NAMES = {
        "keywords_raw": "Keywords",
        "rankings_raw": "SERP Snapshot",
        "history_raw": "SERP History",
        "ai_raw": "AI Analysis",
        "audit_raw": "Site Audit",
        "insights_raw": "Website Tracking & Insights",
        "plan_raw": "Monthly SEO Plan",
        "competitor_raw": "Competitor Snapshot",
    }

    raw_tabs: dict[str, list[dict]] = {}
    for param_name, tab_name in TAB_NAMES.items():
        raw_tabs[param_name] = _get_tab_data(sheet, tab_name)

    # Cache raw data so the API can use it without Sheet access
    save_sheet_data(
        client_name=sheet_name.replace("_", " ").title(),
        report_month=datetime.now().strftime("%B %Y"),
        tabs={tab_name: raw_tabs[param_name] for param_name, tab_name in TAB_NAMES.items()},
    )

    client_name = "Client"
    report_month = datetime.now().strftime("%B %Y")

    facts = build_facts(
        keywords_raw=raw_tabs["keywords_raw"],
        rankings_raw=raw_tabs["rankings_raw"],
        history_raw=raw_tabs["history_raw"],
        ai_raw=raw_tabs["ai_raw"],
        audit_raw=raw_tabs["audit_raw"],
        insights_raw=raw_tabs["insights_raw"],
        plan_raw=raw_tabs["plan_raw"],
        competitor_raw=raw_tabs["competitor_raw"],
        report_month=report_month,
        agency_name="SEO Agency",
        client_name=client_name,
    )

    if not facts.rankings:
        logger.warning("No ranking data found — skipping DOCX generation")
        return

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    client_slug = client_name.lower().replace(" ", "_")

    report_path = output_dir / f"{client_name} Monthly SEO Report {report_month} {timestamp}.docx"
    build_clients_report(facts, str(report_path))
    logger.info("Monthly SEO report saved: %s (%d KB)", report_path.name, report_path.stat().st_size // 1024)

    plan_path = output_dir / f"{client_name} SEO Action Plan {report_month} {timestamp}.docx"
    build_action_plan_docx(facts, str(plan_path))
    logger.info("SEO action plan saved: %s (%d KB)", plan_path.name, plan_path.stat().st_size // 1024)

    try:
        from api.data_cache import cleanup_old_reports
        cleanup_old_reports(output_dir, keep_per_type=10)
    except Exception as e:
        logger.debug("Cleanup skipped: %s", e)


if __name__ == "__main__":
    sys.exit(main())
