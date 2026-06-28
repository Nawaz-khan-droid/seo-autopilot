from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from api.browser_manager import _close_browser
from api.crawl_engine import (
    run_local_opensource_seo_audit, build_defensive_audit_payload,
    _check_link_health, _domain_from_url, captcha_summary,
)
from api.parallel_fetch import (
    _fetch_parallel, _fetch_rankings_via_serp, _fetch_google_trends,
    _capture_serp_preview,
)
from api.facts_assembler import (
    _build_facts_from_audit, _ensure_facts_data, _try_open_sheet,
)
from modules.firecrawl_client import FirecrawlClient, CrawledPage, CrawlResult
from report.docx_technical_audit import build_technical_audit
from report.docx_report import build_clients_report
from report.docx_action_plan import build_action_plan_docx
from report.docx_verifier import verify_all
from report.llm_action_planner import generate_llm_action_plan

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def run_audit(
    url: str,
    sheet_url: str = "",
    mode: str = "single",
    report_month: str = "",
) -> dict[str, Any]:
    try:
        return _run_audit_impl(url, sheet_url, mode, report_month)
    except Exception as e:
        logger.exception("Unhandled error in run_audit for %s", url)
        return {"success": False, "url": url, "generated": [], "errors": [f"Internal error: {e}"]}


def _run_audit_impl(
    url: str,
    sheet_url: str = "",
    mode: str = "single",
    report_month: str = "",
) -> dict[str, Any]:
    month = report_month or datetime.now().strftime("%B %Y")
    fc = FirecrawlClient()

    local_metrics = run_local_opensource_seo_audit(url, crawl_mode=mode)
    defensive_payload = build_defensive_audit_payload(url, local_metrics)

    if not fc.available:
        logger.info("Firecrawl not available — using local analyzer only")
        from modules.client_memory import get_client_memory, build_context_prompt
        client_memory = get_client_memory(url)
        context_prompt = build_context_prompt(client_memory)
        client_name = client_memory.get("client_name", url)
        logger.info("Audit client: %s | niche=%s", client_name, client_memory.get("niche", "?"))

        # Enrich niche via multi-signal classifier
        try:
            from modules.niche_classifier import classify_niche
            title = defensive_payload.get("title", "")
            meta_desc = defensive_payload.get("meta_description", "")
            h1_texts = local_metrics.get("h1_texts", []) or []
            word_count = local_metrics.get("word_count", 0)
            body_snippet = f"[Word count: {word_count}]" if word_count else ""
            niche_result = classify_niche(
                url=url, title=title, meta_description=meta_desc,
                h1_texts=h1_texts, body_snippet=body_snippet,
                tavily_guess=client_memory.get("niche", ""),
            )
            if niche_result.get("source") == "groq_classifier":
                client_memory["niche"] = niche_result["verified_niche"]
                client_memory["category"] = niche_result.get("category", "general")
                context_prompt = build_context_prompt(client_memory)
                logger.info("Niche refined: %s (cat=%s, conf=%.2f)",
                            niche_result["verified_niche"], niche_result.get("category", "?"), niche_result.get("confidence_score", 0))
        except Exception as e:
            logger.warning("Niche classifier failed (non-fatal): %s", e)

        final_metrics = dict(defensive_payload)

        # Fetch PSI, backlinks, GSC, GA4 in parallel
        parallel = _fetch_parallel(url)
        psi_mobile = parallel["psi_mobile"]
        psi_desktop = parallel["psi_desktop"]
        backlinks_data = parallel["backlinks"]
        gsc_data = parallel["gsc"]
        ga4_data = parallel["ga4"]

        # Link health from Playwright-captured links
        link_health = local_metrics.get("link_health", {})
        all_hrefs = link_health.get("all_hrefs", [])
        link_health_data = _check_link_health(all_hrefs, url) if all_hrefs else None

        # Populate CrawlResult from local_metrics if pyseoanalyzer provided multi-page data
        raw_pages = local_metrics.get("_pages", []) or []
        if raw_pages:
            parsed_pages: list[CrawledPage] = []
            for p in raw_pages:
                parsed_pages.append(CrawledPage(
                    url=p.get("url", ""),
                    title=p.get("title"),
                    description=p.get("description"),
                    markdown=p.get("text", "") or "",
                ))
            crawl_result = CrawlResult(pages=parsed_pages, total_pages=len(parsed_pages))
        else:
            crawl_result = CrawlResult(pages=[], total_pages=0)

        facts = _build_facts_from_audit(
            url, crawl_result, None, month,
            local_metrics=local_metrics, client_memory=client_memory,
            pagespeed_mobile=psi_mobile, pagespeed_desktop=psi_desktop,
            backlinks_data=backlinks_data, link_health_data=link_health_data,
            gsc_data=gsc_data, ga4_data=ga4_data,
        )

        try:
            from report.llm_narrative import generate_audit_summary
            audit_data = {
                "pages_audited": defensive_payload["pages_audited"],
                "health_score": defensive_payload["health_score"],
                "total_issues": 0,
                "missing_h1": defensive_payload["missing_h1_count"],
                "missing_meta": defensive_payload["missing_meta_tags"],
                "broken_urls": [],
                "issues_list": [],
            }
            narrative = generate_audit_summary(context_prompt, audit_data)
            if narrative:
                facts.executive_narrative = narrative
        except Exception as e:
            logger.warning("LLM narrative failed (non-fatal): %s", e)

        client_slug = client_name.replace(" ", "_").lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        generated: list[dict[str, Any]] = []
        errors: list[str] = []

        # Ensure no data gaps before generating any deliverable
        _ensure_facts_data(facts)

        # Generate action plan via LLM (GPT 120B SEO skill), falls back to deterministic generator
        try:
            llm_actions = generate_llm_action_plan(facts)
            if llm_actions:
                facts.action_plan = llm_actions
                logger.info("Action plan: %d items from LLM planner", len(llm_actions))
        except Exception as e:
            logger.warning("LLM action planner failed: %s — using deterministic fallback", e)

        serp_preview = _capture_serp_preview(url)
        audit_name = f"{client_name} Technical SEO Audit {month}.docx"
        audit_path = OUTPUT_DIR / audit_name
        try:
            build_technical_audit(facts, str(audit_path), page_preview_bytes=serp_preview)
            generated.append({"type": "audit", "filename": audit_path.name, "size_bytes": audit_path.stat().st_size})
        except Exception as e:
            logger.error("Technical audit generation failed: %s", e, exc_info=True)
            errors.append(f"Technical audit: {e}")

        report_name = f"{client_name} Monthly SEO Report {month}.docx"
        report_path = OUTPUT_DIR / report_name
        trends_kw = client_name.split()[0] if client_name else _domain_from_url(url)
        trends_data = _fetch_google_trends(trends_kw)
        try:
            build_clients_report(facts, str(report_path), google_trends_data=trends_data)
            generated.append({"type": "report", "filename": report_path.name, "size_bytes": report_path.stat().st_size})
        except Exception as e:
            logger.error("Monthly report generation failed: %s", e, exc_info=True)
            errors.append(f"Monthly report: {e}")

        plan_name = f"{client_name} SEO Action Plan {month}.docx"
        plan_path = OUTPUT_DIR / plan_name
        try:
            build_action_plan_docx(facts, str(plan_path))
            generated.append({"type": "plan", "filename": plan_path.name, "size_bytes": plan_path.stat().st_size})
        except Exception as e:
            logger.error("Action plan generation failed: %s", e, exc_info=True)
            errors.append(f"Action plan: {e}")

        # Post-generation quality check
        try:
            gen_paths = [g["filename"] for g in generated]
            qc = verify_all([OUTPUT_DIR / fn for fn in gen_paths])
            for r in qc:
                if not r.get("passed", False):
                    logger.warning("Quality: %s — score=%d issues=%s",
                                    r["path"], r.get("quality_score", 0), r.get("issues", []))
                    errors.append(f"Quality: {Path(r['path']).name} score={r.get('quality_score', 0)}")
        except Exception as e:
            logger.debug("Verifier skipped: %s", e)

        _close_browser()
        return {
            "success": len(generated) > 0,
            "url": url,
            "month": month,
            "generated": generated,
            "download_url": f"/api/reports/download/{generated[0]['filename']}" if generated else "",
            "errors": errors,
            "metrics": final_metrics,
"niche": client_memory.get("niche", client_memory.get("business_type", "")),
            "client": client_name,
        }

    # Step 0: Tavily client discovery
    from modules.client_memory import get_client_memory, build_context_prompt
    client_memory = get_client_memory(url)
    context_prompt = build_context_prompt(client_memory)
    client_name = client_memory.get("client_name", url)
    logger.info("Audit client: %s | niche=%s", client_name, client_memory.get("niche", "?"))

    # Enrich niche via multi-signal classifier
    try:
        from modules.niche_classifier import classify_niche
        title = defensive_payload.get("title", "")
        meta_desc = defensive_payload.get("meta_description", "")
        h1_texts = local_metrics.get("h1_texts", []) or []
        word_count = local_metrics.get("word_count", 0)
        body_snippet = f"[Word count: {word_count}]" if word_count else ""
        niche_result = classify_niche(
            url=url, title=title, meta_description=meta_desc,
            h1_texts=h1_texts, body_snippet=body_snippet,
            tavily_guess=client_memory.get("niche", ""),
        )
        if niche_result.get("source") == "groq_classifier":
            client_memory["niche"] = niche_result["verified_niche"]
            client_memory["category"] = niche_result.get("category", "general")
            context_prompt = build_context_prompt(client_memory)
    except Exception as e:
        logger.warning("Niche classifier failed (non-fatal): %s", e)

    # Link health from Playwright-captured links
    link_health = local_metrics.get("link_health", {})
    all_hrefs = link_health.get("all_hrefs", [])
    link_health_data = _check_link_health(all_hrefs, url) if all_hrefs else None

    final_metrics = dict(defensive_payload)

    # Fetch PSI, backlinks, GSC, GA4 in parallel while crawling
    parallel = _fetch_parallel(url)
    psi_mobile = parallel["psi_mobile"]
    psi_desktop = parallel["psi_desktop"]
    backlinks_data = parallel["backlinks"]
    gsc_data = parallel["gsc"]
    ga4_data = parallel["ga4"]

    logger.info("Audit: crawling %s (mode=%s)", url, mode)
    if mode == "full":
        crawl_result = fc.crawl_site(url, max_pages=15)
    else:
        page = fc.scrape_page(url)
        crawl_result = CrawlResult(pages=[page], total_pages=1)
        if page.status_code and page.status_code >= 400:
            crawl_result.broken_urls.append(url)

    if not crawl_result.pages:
        logger.warning("Firecrawl returned no pages — using local analyzer as fallback")
        crawl_result = CrawlResult(pages=[], total_pages=0)

    sheet_tabs = _try_open_sheet(sheet_url) if sheet_url else None

    facts = _build_facts_from_audit(
        url, crawl_result, sheet_tabs, month,
        local_metrics=local_metrics, client_memory=client_memory,
        pagespeed_mobile=psi_mobile, pagespeed_desktop=psi_desktop,
        backlinks_data=backlinks_data, link_health_data=link_health_data,
        gsc_data=gsc_data, ga4_data=ga4_data,
    )

    try:
        from report.llm_narrative import generate_audit_summary
        def _safe_val(e: Any) -> Any:
            if hasattr(e, "is_available") and not e.is_available:
                return None
            return getattr(e, "value", e) if hasattr(e, "value") else e

        crawl_pages = crawl_result.pages or []
        audit_data = {
            "pages_audited": len(crawl_pages) or defensive_payload["pages_audited"],
            "health_score": _safe_val(facts.technical.health_score) or defensive_payload["health_score"],
            "total_issues": _safe_val(facts.technical.total_issues) or 0,
            "missing_h1": _safe_val(facts.technical.missing_h1) or defensive_payload["missing_h1_count"],
            "missing_meta": _safe_val(facts.technical.missing_meta) or defensive_payload["missing_meta_tags"],
            "broken_urls": crawl_result.broken_urls,
            "issues_list": [{"page": i.page, "issue_text": i.issue_text, "severity": i.severity} for i in facts.technical.issues_list],
        }
        narrative = generate_audit_summary(context_prompt, audit_data)
        if narrative:
            facts.executive_narrative = narrative
    except Exception as e:
        logger.warning("LLM narrative generation failed (non-fatal): %s", e)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated: list[dict[str, Any]] = []
    errors: list[str] = []

    # Ensure no data gaps before generating any deliverable
    _ensure_facts_data(facts)

    # Generate action plan via LLM (GPT 120B SEO skill), falls back to deterministic generator
    try:
        llm_actions = generate_llm_action_plan(facts)
        if llm_actions:
            facts.action_plan = llm_actions
            logger.info("Action plan: %d items from LLM planner", len(llm_actions))
    except Exception as e:
        logger.warning("LLM action planner failed: %s — using deterministic fallback", e)

    audit_name = f"{client_name} Technical SEO Audit {month}.docx"
    audit_path = OUTPUT_DIR / audit_name
    serp_preview = _capture_serp_preview(url)
    try:
        build_technical_audit(facts, str(audit_path), page_preview_bytes=serp_preview)
        generated.append({"type": "audit", "filename": audit_path.name, "size_bytes": audit_path.stat().st_size})
    except Exception as e:
        logger.error("Technical audit generation failed: %s", e, exc_info=True)
        errors.append(f"Technical audit: {e}")

    report_name = f"{client_name} Monthly SEO Report {month}.docx"
    report_path = OUTPUT_DIR / report_name
    trends_kw = client_name.split()[0] if client_name else _domain_from_url(url)
    trends_data = _fetch_google_trends(trends_kw)
    try:
        build_clients_report(facts, str(report_path), google_trends_data=trends_data)
        generated.append({"type": "report", "filename": report_path.name, "size_bytes": report_path.stat().st_size})
    except Exception as e:
        logger.error("Monthly report generation failed: %s", e, exc_info=True)
        errors.append(f"Monthly report: {e}")

    plan_name = f"{client_name} SEO Action Plan {month}.docx"
    plan_path = OUTPUT_DIR / plan_name
    try:
        build_action_plan_docx(facts, str(plan_path))
        generated.append({"type": "plan", "filename": plan_path.name, "size_bytes": plan_path.stat().st_size})
    except Exception as e:
        logger.error("Action plan generation failed: %s", e, exc_info=True)
        errors.append(f"Action plan: {e}")

    # Post-generation quality check
    try:
        gen_paths = [g["filename"] for g in generated]
        qc = verify_all([OUTPUT_DIR / fn for fn in gen_paths])
        for r in qc:
            if not r.get("passed", False):
                logger.warning("Quality: %s — score=%d issues=%s",
                                r["path"], r.get("quality_score", 0), r.get("issues", []))
                errors.append(f"Quality: {Path(r['path']).name} score={r.get('quality_score', 0)}")
    except Exception as e:
        logger.debug("Verifier skipped: %s", e)

    _close_browser()

    result: dict[str, Any] = {
        "success": len(generated) > 0,
        "url": url,
        "month": month,
        "generated": generated,
        "metrics": final_metrics,
        "niche": client_memory.get("niche", client_memory.get("business_type", "")),
        "client": client_name,
    }
    if generated:
        result["download_url"] = f"/api/reports/download/{generated[0]['filename']}"
    if errors:
        result["errors"] = errors
    return result
