from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from modules.http_pool import sync_client
from modules.url_utils import resolve_and_validate_target

from modules.firecrawl_client import CrawledPage, CrawlResult
from modules.sheet_client import SheetClient as _SheetClient
from report.evidence import Evidence
from report.facts import (
    ActionItem, CWVData, Kpidata, RankingRow, ReportFacts,
    TechnicalData, TechnicalIssue, ReportMetadata,
)
from api.parallel_fetch import _fetch_rankings_via_serp

logger = logging.getLogger(__name__)


def _try_open_sheet(sheet_url: str) -> dict[str, list[dict[str, Any]]] | None:
    if not sheet_url or "spreadsheets" not in sheet_url.lower():
        return None
    try:
        from config.settings import CREDENTIALS_PATH
        if not CREDENTIALS_PATH or not Path(CREDENTIALS_PATH).exists():
            logger.warning("Sheet credentials not available")
            return None
        sheet = _SheetClient(credentials_path=CREDENTIALS_PATH, sheet_url=sheet_url)
        result: dict[str, list[dict[str, Any]]] = {}
        for ws in sheet.sheet.worksheets():
            try:
                records = ws.get_all_records()
                if records:
                    result[ws.title] = records
            except Exception:
                continue
        if result:
            logger.info("Read %d tab(s) from shared sheet", len(result))
            return result
    except Exception as e:
        logger.warning("Could not open shared sheet: %s", e)
    return None


def _ensure_facts_data(facts: ReportFacts) -> None:
    logger.info("Data completeness: %d rankings, %s CWV, %s backlinks, site=%s",
                 len(facts.rankings),
                 "OK" if facts.cwv.mobile_score.is_available else "MISSING",
                 "OK" if facts.backlinks.total_backlinks.is_available else "MISSING",
                 bool(facts.site_info.title_tag) or "MISSING",
                 )


def _build_facts_from_audit(
    url: str,
    crawl_result: CrawlResult,
    sheet_data: dict[str, list[dict[str, Any]]] | None,
    report_month: str,
    local_metrics: dict[str, Any] | None = None,
    client_memory: dict[str, Any] | None = None,
    pagespeed_mobile: dict[str, Any] | None = None,
    pagespeed_desktop: dict[str, Any] | None = None,
    backlinks_data: dict[str, Any] | None = None,
    link_health_data: dict[str, Any] | None = None,
    gsc_data: dict | None = None,
    ga4_data: dict | None = None,
    seo_rules_issues: list[dict[str, Any]] | None = None,
) -> ReportFacts:
    facts = ReportFacts(
        metadata=ReportMetadata(
            client_name=url,
            agency_name="SEO Agency",
            report_month=report_month,
            generated_at=datetime.now().isoformat(timespec="seconds"),
        ),
    )

    if sheet_data:
        for tab_name, records in sheet_data.items():
            tl = tab_name.lower()
            if any(kw in tl for kw in ["keyword", "rank", "position", "query"]):
                for rec in records:
                    kw = str(rec.get("Keyword") or rec.get("keyword") or rec.get("Query") or rec.get("query", "")).strip()
                    pos = str(rec.get("Position") or rec.get("position", ""))
                    if kw and pos:
                        facts.rankings.append(RankingRow(
                            keyword=kw,
                            position=Evidence.verified(pos, f"Sheet:{tab_name}"),
                        ))
            # Read backlink data from sheet tabs
            if any(kw in tl for kw in ["backlink", "link", "referring", "domain"]):
                for rec in records:
                    total_bl = rec.get("total_backlinks") or rec.get("Total Backlinks") or rec.get("backlinks") or rec.get("Backlinks")
                    ref_dom = rec.get("ref_domains") or rec.get("Referring Domains") or rec.get("ref_domains") or rec.get("Ref Domains")
                    dr_val = rec.get("domain_rating") or rec.get("Domain Rating") or rec.get("DR") or rec.get("DA")
                    if total_bl or ref_dom or dr_val:
                        facts.backlinks.status = "AVAILABLE"
                        if total_bl:
                            facts.backlinks.total_backlinks = Evidence.verified(str(total_bl), f"Sheet:{tab_name}")
                        if ref_dom:
                            facts.backlinks.ref_domains = Evidence.verified(str(ref_dom), f"Sheet:{tab_name}")
                        if dr_val:
                            facts.backlinks.domain_rating = Evidence.verified(str(dr_val), f"Sheet:{tab_name}")
                        break  # Use first row with backlink data

    if not facts.rankings:
        serp_rows = _fetch_rankings_via_serp(url, existing_metrics=local_metrics)
        facts.rankings.extend(serp_rows)

    if backlinks_data:
        bl_status = backlinks_data.get("status", "MISSING")
        if bl_status == "AWAITING_DATA":
            facts.backlinks.status = "AWAITING_DATA"
        elif backlinks_data.get("total_backlinks") not in (None, "Data Pending"):
            bsrc = backlinks_data.get("source", "Backlink Checker")
            facts.backlinks.status = "AVAILABLE"
            facts.backlinks.total_backlinks = Evidence.verified(str(backlinks_data["total_backlinks"]), bsrc)
            if backlinks_data.get("ref_domains") not in (None, "Data Pending"):
                facts.backlinks.ref_domains = Evidence.verified(str(backlinks_data["ref_domains"]), bsrc)
            if backlinks_data.get("dofollow") not in (None, "Data Pending"):
                facts.backlinks.dofollow_count = Evidence.verified(str(backlinks_data["dofollow"]), bsrc)
            if backlinks_data.get("nofollow") not in (None, "Data Pending"):
                facts.backlinks.nofollow_count = Evidence.verified(str(backlinks_data["nofollow"]), bsrc)
        elif bl_status == "OPR_ONLY":
            facts.backlinks.status = "OPR_ONLY"
            dr_val = backlinks_data.get("dr")
            if dr_val:
                facts.backlinks.domain_rating = Evidence.verified(str(dr_val), backlinks_data.get("source", "OpenPageRank"))

    local = local_metrics or {}
    pages_data = crawl_result.pages or []

    facts.site_info.title_tag = local.get("title", "")
    facts.site_info.meta_description = local.get("meta_description", "")
    facts.site_info.h1_texts = local.get("h1_texts", []) or []
    facts.site_info.h1_count = len(facts.site_info.h1_texts) or local.get("h1_count", 0)
    facts.site_info.word_count = int(local.get("word_count", 0))
    og_found = bool(local.get("has_og_tags", False))
    facts.site_info.has_og_tags = Evidence.verified("Yes" if og_found else "No", "Playwright DOM")
    try:
        domain = urlparse(url).netloc
        robots_url = f"https://{domain}/robots.txt"
        if resolve_and_validate_target(robots_url):
            r = sync_client().head(robots_url, timeout=5.0)
            facts.site_info.has_robots_txt = Evidence.verified("Found" if r.status_code < 400 else "Not Found", "HTTP HEAD")
        else:
            facts.site_info.has_robots_txt = Evidence.missing()
    except Exception:
        facts.site_info.has_robots_txt = Evidence.missing()
    try:
        sitemap_url = f"https://{domain}/sitemap.xml"
        if resolve_and_validate_target(sitemap_url):
            r = sync_client().head(sitemap_url, timeout=5.0)
            facts.site_info.has_sitemap_xml = Evidence.verified("Found" if r.status_code < 400 else "Not Found", "HTTP HEAD")
        else:
            facts.site_info.has_sitemap_xml = Evidence.missing()
    except Exception:
        facts.site_info.has_sitemap_xml = Evidence.missing()

    total_pages = len(pages_data) or local.get("pages_audited", 1)
    issues_list: list[TechnicalIssue] = []
    missing_titles = local.get("missing_meta_tags", 0)
    missing_h1 = local.get("missing_h1_count", 0)
    missing_alt = local.get("missing_alt_tags", 0)
    thin_pages = local.get("thin_pages_detected", 0)
    health_base = local.get("health_score")

    for page in pages_data:
        if not page.title:
            missing_titles += 1
        if page.status_code and page.status_code >= 400:
            issues_list.append(TechnicalIssue(
                page=page.url,
                issue_text=f"HTTP {page.status_code}",
                severity="Critical" if page.status_code >= 500 else "High",
            ))
        if page.markdown and not re.search(r'^# ', page.markdown, re.MULTILINE):
            missing_h1 += 1

    # Add on-page issues from crawl counts
    if missing_h1:
        issues_list.append(TechnicalIssue(
            page=url, issue_text=f"{missing_h1} page(s) missing H1 tag",
            severity="Warning",
        ))
    if missing_titles:
        issues_list.append(TechnicalIssue(
            page=url, issue_text=f"{missing_titles} page(s) missing meta description",
            severity="Warning",
        ))
    if missing_alt:
        issues_list.append(TechnicalIssue(
            page=url, issue_text=f"{missing_alt} images missing alt text",
            severity="Warning",
        ))
    if thin_pages:
        issues_list.append(TechnicalIssue(
            page=url, issue_text=f"{thin_pages} thin page(s) detected (< 300 words)",
            severity="Medium",
        ))

    if seo_rules_issues:
        rules_penalty = min(sum(3 for i in seo_rules_issues if i.get("severity") in ("critical", "warning")) +
                            sum(1 for i in seo_rules_issues if i.get("severity") == "info"), 30)
        health_base = (health_base or 85) - rules_penalty
        for ri in seo_rules_issues:
            issues_list.append(TechnicalIssue(
                page=ri.get("url", url),
                issue_text=f"[{ri['rule_id']}] {ri['message']}" if ri.get("message") else ri.get("rule_id", "SEO Issue"),
                severity=ri.get("severity", "info").capitalize(),
            ))

    health_value = str(max(25, min(100, int(health_base)))) if health_base is not None else None
    facts.technical = TechnicalData(
        health_score=Evidence.verified(health_value, "SEO Rules Engine (269 rules)") if health_value else Evidence.missing(),
        pages_audited=Evidence.verified(str(total_pages), "SEO Analyzer + Firecrawl"),
        total_issues=Evidence.verified(str(len(issues_list)), "SEO Analyzer + Firecrawl"),
        missing_h1=Evidence.verified(str(missing_h1), "SEO Analyzer + Firecrawl"),
        missing_meta=Evidence.verified(str(missing_titles), "SEO Analyzer + Firecrawl"),
        missing_alt=Evidence.verified(str(missing_alt), "SEO Analyzer + Firecrawl"),
        thin_pages=Evidence.verified(str(thin_pages), "SEO Analyzer + Firecrawl"),
        has_schema=Evidence.verified(
            "Yes" if local.get("has_yoast_schema") else "No",
            "SEO Analyzer",
        ),
        issues_list=issues_list,
    )

    def _psi_ev(d: dict[str, Any] | None, key: str) -> Evidence:
        if d is None:
            return Evidence.missing()
        if d.get("error"):
            logger.warning("PSI %s error for '%s': %s", d.get("strategy", "?"), key, d["error"])
            return Evidence.missing()
        val = d.get(key)
        if val is not None:
            return Evidence.verified(str(val), f"PSI {d.get('strategy', '?')}")
        return Evidence.missing()

    facts.cwv = CWVData(
        mobile_score=_psi_ev(pagespeed_mobile, "score"),
        desktop_score=_psi_ev(pagespeed_desktop, "score"),
        lcp_seconds=_psi_ev(pagespeed_mobile, "lcp_seconds"),
        inp_ms=_psi_ev(pagespeed_mobile, "inp_ms") if (pagespeed_mobile or {}).get("has_field_data") else Evidence.missing(),
        cls_score=_psi_ev(pagespeed_mobile, "cls_score"),
        render_blocking_ms=Evidence.missing(),
    )

    if link_health_data:
        facts.backlinks.onpage_total_links = Evidence.verified(str(link_health_data.get("total_links_checked", 0)), "Playwright Link Audit")
        facts.backlinks.onpage_internal_links = Evidence.verified(str(link_health_data.get("internal_links", 0)), "Playwright Link Audit")
        facts.backlinks.onpage_external_links = Evidence.verified(str(link_health_data.get("external_links", 0)), "Playwright Link Audit")

        broken_list = link_health_data.get("broken_links", [])
        redirect_list = link_health_data.get("redirect_links", [])
        if broken_list or redirect_list:
            for bl in broken_list[:5]:
                facts.technical.issues_list.append(TechnicalIssue(
                    page=bl, issue_text="Broken link (404/5xx)", severity="High",
                ))
            for rl in redirect_list[:5]:
                facts.technical.issues_list.append(TechnicalIssue(
                    page=rl, issue_text="Redirect chain", severity="Medium",
                ))
    elif pages_data:
        total_links = 0
        internal_links = 0
        external_links = 0
        domain = urlparse(url).netloc
        for p in pages_data:
            if p.markdown:
                links = re.findall(r'\[.*?\]\((https?://[^\s)]+)\)', p.markdown)
                for ln in links:
                    total_links += 1
                    if domain in ln:
                        internal_links += 1
                    else:
                        external_links += 1
        if total_links > 0:
            facts.backlinks.onpage_total_links = Evidence.verified(str(total_links), "Firecrawl Markdown")
            facts.backlinks.onpage_internal_links = Evidence.verified(str(internal_links), "Firecrawl Markdown")
            facts.backlinks.onpage_external_links = Evidence.verified(str(external_links), "Firecrawl Markdown")

    if gsc_data:
        facts.kpis = Kpidata(
            clicks=Evidence.verified(str(gsc_data.get("clicks", 0)), "Google Search Console API"),
            impressions=Evidence.verified(str(gsc_data.get("impressions", 0)), "Google Search Console API"),
            clicks_change=Evidence.verified(str(gsc_data.get("clicks_change", 0)), "Google Search Console API"),
            impressions_change=Evidence.verified(str(gsc_data.get("impressions_change", 0)), "Google Search Console API"),
        )
    elif sheet_data:
        for tab_name, records in sheet_data.items():
            tl = tab_name.lower()
            if any(x in tl for x in ["traffic", "click", "impression", "session", "performance"]):
                clicks_total = 0
                impressions_total = 0
                for rec in records:
                    try:
                        clicks_total += int(float(str(rec.get("Clicks") or rec.get("clicks", 0))))
                    except (ValueError, TypeError):
                        pass
                    try:
                        impressions_total += int(float(str(rec.get("Impressions") or rec.get("impressions", 0))))
                    except (ValueError, TypeError):
                        pass
                facts.kpis = Kpidata(
                    clicks=Evidence.verified(str(clicks_total), f"Sheet:{tab_name}"),
                    impressions=Evidence.verified(str(impressions_total), f"Sheet:{tab_name}"),
                )

    if ga4_data:
        facts.kpis.organic_users = Evidence.verified(str(ga4_data.get("organic_users", 0)), "Google Analytics 4 API")
        facts.kpis.sessions = Evidence.verified(str(ga4_data.get("sessions", 0)), "Google Analytics 4 API")

    return facts
