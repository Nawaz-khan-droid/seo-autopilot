from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
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
from modules.seo_rules import run_seo_rules
from report.docx_technical_audit import build_technical_audit
from report.docx_report import build_clients_report
from report.docx_action_plan import build_action_plan_docx
from report.docx_verifier import verify_all
from report.llm_action_planner import generate_llm_action_plan

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _quick_page_scan(url: str) -> dict[str, Any]:
    """Fetch page via HTTP + BS4. Returns guaranteed metrics. Runs in < 5s, never throws."""
    result: dict[str, Any] = {
        "url": url, "health_score": 85, "pages_audited": 1,
        "missing_h1_count": 0, "missing_meta_tags": 0, "missing_alt_tags": 0,
        "total_images_found": 0, "thin_pages_detected": 0, "has_yoast_schema": False,
        "title": "", "meta_description": "", "h1_texts": [],
        "keywords_tracked": 0, "rankings_top_3": 0, "rankings_top_10": 0,
        "backlinks_count": "No Data",
    }
    try:
        import httpx
        from bs4 import BeautifulSoup
        r = httpx.get(url, timeout=10, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code >= 400:
            result["health_score"] = 50
            return result
        soup = BeautifulSoup(r.text, "html.parser")
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            result["title"] = title_tag.get_text(strip=True)
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            result["meta_description"] = meta_tag["content"].strip()
        h1s = soup.find_all("h1")
        result["h1_texts"] = [h.get_text(strip=True) for h in h1s if h.get_text(strip=True)]
        result["missing_h1_count"] = 0 if h1s else 1
        all_imgs = soup.find_all("img")
        result["total_images_found"] = len(all_imgs)
        result["missing_alt_tags"] = sum(1 for img in all_imgs if not img.get("alt") or not img["alt"].strip())
        body_text = soup.get_text(strip=True)
        word_count = len(body_text.split()) if body_text else 0
        result["thin_pages_detected"] = 1 if word_count < 300 else 0
        # Schema
        for s in soup.find_all("script", type="application/ld+json"):
            if s.string and "@type" in s.string:
                result["has_yoast_schema"] = True
                break
        # OG tags
        og_tags = soup.find_all("meta", property=True)
        result["has_og_tags"] = any(m.get("property", "").startswith("og:") for m in og_tags)
        # Keywords from title
        if result["title"]:
            words = [w for w in result["title"].split() if len(w) > 3]
            if words:
                result["keywords_tracked"] = max(1, min(len(words), 5))
        result["health_score"] = max(40, min(100, 100 - result["missing_h1_count"] * 10 - result["missing_alt_tags"] // 5))
    except Exception:
        pass
    return result


def run_audit(
    url: str,
    sheet_url: str = "",
    mode: str = "single",
    report_month: str = "",
) -> dict[str, Any]:
    return _run_audit_impl(url, sheet_url, mode, report_month)


def _safe_val(e: Any) -> Any:
    if hasattr(e, "is_available") and not e.is_available:
        return None
    return getattr(e, "value", e) if hasattr(e, "value") else e


def _generate_narrative(
    facts: Any,
    crawl_result: CrawlResult,
    context_prompt: str,
    defensive_payload: dict[str, Any],
) -> None:
    """Generate LLM narrative for the audit — uses crawl data if available,
    falls back to defensive payload values when crawl returned no pages."""
    try:
        from report.llm_narrative import generate_audit_summary

        crawl_pages = crawl_result.pages or []
        audit_data = {
            "pages_audited": len(crawl_pages) or defensive_payload["pages_audited"],
            "health_score": _safe_val(facts.technical.health_score) or defensive_payload["health_score"],
            "total_issues": _safe_val(facts.technical.total_issues) or 0,
            "missing_h1": _safe_val(facts.technical.missing_h1) or defensive_payload["missing_h1_count"],
            "missing_meta": _safe_val(facts.technical.missing_meta) or defensive_payload["missing_meta_tags"],
            "broken_urls": crawl_result.broken_urls,
            "issues_list": [
                {"page": i.page, "issue_text": i.issue_text, "severity": i.severity}
                for i in facts.technical.issues_list
            ],
        }
        narrative = generate_audit_summary(context_prompt, audit_data)
        if narrative:
            facts.executive_narrative = narrative
    except Exception as e:
        logger.warning("LLM narrative generation failed (non-fatal): %s", e)


def _run_llm_action_plan(facts: Any) -> None:
    """Generate action plan via LLM with 30s timeout."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(generate_llm_action_plan, facts)
        llm_actions = future.result(timeout=30.0)
        if llm_actions:
            facts.action_plan = llm_actions
            logger.info("Action plan: %d items from LLM planner", len(llm_actions))
    except TimeoutError:
        logger.warning("LLM action planner timed out after 30s — using deterministic fallback")
    except Exception as e:
        logger.warning("LLM action planner failed: %s — using deterministic fallback", e)
    finally:
        pool.shutdown(wait=False)


def _generate_deliverables(
    facts: Any,
    client_name: str,
    month: str,
    url: str,
    final_metrics: dict[str, Any],
    client_memory: dict[str, Any],
    context_prompt: str,
    crawl_result: CrawlResult,
    defensive_payload: dict[str, Any],
) -> dict[str, Any]:
    """Shared deliverable generation for both Firecrawl and local paths."""
    # Enrich metrics with ranking/backlink data from facts
    rankings = facts.rankings or []
    final_metrics["keywords_tracked"] = len(rankings)
    top3 = 0
    top10 = 0
    for r in rankings:
        if r.position.is_available and r.position.value is not None:
            try:
                pos = int(str(r.position.value))
                if pos <= 3:
                    top3 += 1
                if pos <= 10:
                    top10 += 1
            except (ValueError, TypeError):
                pass
    # Count discovered keywords from page title as a fallback
    if not rankings:
        title = final_metrics.get("title", "") or ""
        if title:
            discovered = [w for w in title.split() if len(w) > 3]
            final_metrics["keywords_tracked"] = max(1, min(len(discovered), 5))
    final_metrics["rankings_top_3"] = top3
    final_metrics["rankings_top_10"] = top10
    if facts.backlinks.total_backlinks.is_available and facts.backlinks.total_backlinks.value is not None:
        final_metrics["backlinks_count"] = facts.backlinks.total_backlinks.value
    elif facts.backlinks.domain_rating.is_available and facts.backlinks.domain_rating.value is not None:
        final_metrics["backlinks_count"] = f"DR {facts.backlinks.domain_rating.value}"
    elif facts.backlinks.status == "AWAITING_DATA":
        final_metrics["backlinks_count"] = "Data Pending"
    else:
        final_metrics["backlinks_count"] = "No Data"

    _generate_narrative(facts, crawl_result, context_prompt, defensive_payload)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated: list[dict[str, Any]] = []
    errors: list[str] = []

    _ensure_facts_data(facts)
    _run_llm_action_plan(facts)

    try:
        serp_preview = _capture_serp_preview(url)
    except Exception:
        serp_preview = None

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
        "issues": [
            {"page": i.page, "issue_text": i.issue_text, "severity": i.severity}
            for i in facts.technical.issues_list
        ],
        "rankings": [
            {"keyword": r.keyword, "position": getattr(r.position, "value", r.position)}
            for r in (facts.rankings or [])
        ],
    }
    if generated:
        result["download_url"] = f"/api/reports/download/{generated[0]['filename']}"
    if errors:
        result["errors"] = errors
    return result


def _run_audit_impl(
    url: str,
    sheet_url: str = "",
    mode: str = "single",
    report_month: str = "",
) -> dict[str, Any]:
    month = report_month or datetime.now().strftime("%B %Y")
    fc = FirecrawlClient()

    # Log API key status so missing config is visible in logs
    import os as _os
    _key_status = {
        "SERPAPI_KEY": bool(_os.environ.get("SERPAPI_KEY")),
        "SEARCHAPI_API_KEY": bool(_os.environ.get("SEARCHAPI_API_KEY")),
        "APIFY_API_KEY": bool(_os.environ.get("APIFY_API_KEY")),
        "GROQ_API_KEY": bool(_os.environ.get("GROQ_API_KEY")),
        "PAGESPEED_API_KEY": bool(_os.environ.get("PAGESPEED_API_KEY")),
    }
    _configured = [k for k, v in _key_status.items() if v]
    _missing = [k for k, v in _key_status.items() if not v]
    logger.info("API keys configured: %s | missing: %s", _configured or "none", _missing or "none")

    local_metrics = run_local_opensource_seo_audit(url, crawl_mode=mode)
    defensive_payload = build_defensive_audit_payload(url, local_metrics)

    # ── Shared preamble: client context + niche classifier ──
    from modules.client_memory import get_client_memory, build_context_prompt

    client_memory = get_client_memory(url)
    context_prompt = build_context_prompt(client_memory)
    client_name = client_memory.get("client_name", url)
    logger.info("Audit client: %s | niche=%s", client_name, client_memory.get("niche", "?"))

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
                        niche_result["verified_niche"], niche_result.get("category", "?"),
                        niche_result.get("confidence_score", 0))
    except Exception as e:
        logger.warning("Niche classifier failed (non-fatal): %s", e)

    # ── Shared data fetch: parallel PSI/backlinks/GSC/GA4 + link health ──
    link_health = local_metrics.get("link_health", {})
    all_hrefs = link_health.get("all_hrefs", [])

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        parallel_future = pool.submit(_fetch_parallel, url)
        link_health_future = pool.submit(_check_link_health, all_hrefs, url) if all_hrefs else None

    try:
        parallel = parallel_future.result()
    except Exception as e:
        logger.error("Parallel fetch failed: %s", e)
        parallel = {"psi_mobile": {}, "psi_desktop": {}, "backlinks": {}, "gsc": None, "ga4": None}

    psi_mobile = parallel["psi_mobile"]
    psi_desktop = parallel["psi_desktop"]
    backlinks_data = parallel["backlinks"]
    gsc_data = parallel["gsc"]
    ga4_data = parallel["ga4"]

    final_metrics = dict(defensive_payload)

    try:
        link_health_data = link_health_future.result() if link_health_future is not None else None
    except Exception as e:
        logger.warning("Link health check failed: %s", e)
        link_health_data = None

    # ── Branch: crawl source (only unique part per path) ──
    if not fc.available:
        logger.info("Firecrawl not available — using local analyzer only")
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
        sheet_tabs = None
    else:
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

    # ── SEO Rules Engine (269 rules, DuckDB-backed) ──
    seo_rules_issues = run_seo_rules(url, local_metrics)

    # ── Shared facts assembly ──
    facts = _build_facts_from_audit(
        url, crawl_result, sheet_tabs, month,
        local_metrics=local_metrics, client_memory=client_memory,
        pagespeed_mobile=psi_mobile, pagespeed_desktop=psi_desktop,
        backlinks_data=backlinks_data, link_health_data=link_health_data,
        gsc_data=gsc_data, ga4_data=ga4_data,
        seo_rules_issues=seo_rules_issues,
    )

    return _generate_deliverables(
        facts, client_name, month, url, final_metrics,
        client_memory, context_prompt, crawl_result, defensive_payload,
    )
