import logging
import os
import time
from datetime import datetime
from typing import Any

from report.charts import rank_trend_chart
from report.facts import ReportFacts
from report.facts_loader import build_facts
from report.llm_narrative import generate_narrative
from report.renderer import build_pdf
from report.sheet_mapper import discover, validate_data

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, sheet, groq_client, agency_name: str = "SEO Agency",
                 client_name: str = "Client", output_dir: str = "output"):
        self.sheet = sheet
        self.groq = groq_client
        self.agency_name = agency_name
        self.client_name = client_name
        self.output_dir = output_dir

    def run(self, report_month: str | None = None, output_format: str = "pdf") -> str:
        if not report_month:
            report_month = datetime.now().strftime("%B %Y")
        output_format = output_format.lower().strip()

        os.makedirs(self.output_dir, exist_ok=True)

        # ── 1. Discover sheet structure (works with ANY client sheet) ──
        logger.info("Discovering sheet structure...")
        data = discover(self.sheet)
        warnings = validate_data(data)
        for w in warnings:
            logger.warning("Sheet warning: %s", w)

        # Extract raw data from discovered structure
        keywords_raw = data.get("keywords", [])
        rankings_raw = data.get("serp_snapshot", [])
        history_raw = data.get("serp_history", [])
        ai_raw = data.get("ai_analysis", [])
        audit_raw = data.get("site_audit", [])
        insights_raw = data.get("website_insights", [])
        plan_raw = data.get("action_plan", [])
        competitor_raw = data.get("competitors", [])

        logger.info(
            f"Discovered: {len(keywords_raw)} kw, {len(rankings_raw)} snapshots, "
            f"{len(history_raw)} history, {len(audit_raw)} audit records"
        )

        # ── 2. Generate rank trend charts ──
        chart_images: dict[str, bytes] = {}
        for rec in rankings_raw:
            kw = str(rec.get("Keyword", "") or "").strip()
            if kw:
                try:
                    img_bytes = rank_trend_chart(kw, history_raw)
                    if img_bytes and len(img_bytes) > 200:
                        chart_images[kw] = img_bytes
                except Exception as e:
                    logger.warning("Chart failed for '%s': %s", kw, e)
        logger.info(f"{len(chart_images)} charts generated")

        # ── 3. Capture screenshots (top 3 ranked keywords) ──
        screenshots: dict[str, dict[str, bytes | None]] = {}
        try:
            from report.screenshots import capture_screenshots as capture_ss
            sorted_rankings = sorted(
                [r for r in rankings_raw
                 if str(r.get("Position", "")).strip().lower() not in ("not found", "", "n/a")],
                key=lambda r: int(r.get("Position", 999))
                if str(r.get("Position", "")).strip().isdigit() else 999,
            )[:3]
            for r in sorted_rankings:
                url = r.get("Target URL", "") or r.get("Ranking URL", "")
                if not url:
                    continue
                try:
                    shots = capture_ss(url)
                    kw = r.get("Keyword", "")
                    if shots.get("desktop_png") or shots.get("mobile_png"):
                        screenshots[kw] = shots
                except Exception as e:
                    logger.warning("Screenshot failed for '%s': %s", r.get("Keyword", "?"), e)
        except ImportError as e:
            logger.warning("Screenshot module unavailable: %s", e)
        logger.info(f"{len(screenshots)} screenshots captured")

        psi_screenshots: dict[str, bytes | None] = {}

        # ── 4. Build ReportFacts from discovered data ──
        facts: ReportFacts = build_facts(
            keywords_raw=keywords_raw,
            rankings_raw=rankings_raw,
            history_raw=history_raw,
            ai_raw=ai_raw,
            audit_raw=audit_raw,
            insights_raw=insights_raw,
            plan_raw=plan_raw,
            competitor_raw=competitor_raw,
            report_month=report_month,
            agency_name=self.agency_name,
            client_name=self.client_name,
        )

        # ── 5. Generate LLM executive narrative ──
        llm_data = {
            "report_month": report_month,
            "rankings": [
                {
                    "Keyword": r.keyword,
                    "Target URL": r.target_url,
                    "Position": str(r.position.value) if r.position.is_available else "",
                    "Change": str(r.change.value) if r.change.is_available else "",
                    "Data Availability": str(r.data_availability.value) if r.data_availability.is_available else "",
                }
                for r in facts.rankings
            ],
            "audit_issues": [
                {"URL": iss.page, "Issues": iss.issue_text, "Images Missing Alt": 0}
                for iss in facts.technical.issues_list
            ],
            "insights": [
                {
                    "Desktop PSI": str(facts.cwv.desktop_score.value) if facts.cwv.desktop_score.is_available else "",
                    "Mobile PSI": str(facts.cwv.mobile_score.value) if facts.cwv.mobile_score.is_available else "",
                }
            ],
            "plan_items": [
                {"Item": a.task, "Priority": a.priority}
                for a in facts.action_plan
            ],
        }
        narrative = generate_narrative(llm_data, self.groq)
        if not narrative:
            imp = sum(1 for r in facts.rankings if r.change.is_available and str(r.change.value).startswith("+"))
            drp = sum(1 for r in facts.rankings if r.change.is_available and str(r.change.value).startswith("-"))
            nf = sum(1 for r in facts.rankings if str(r.position.value).strip().lower() == "not found")
            narrative = (
                f"{self.agency_name} tracked {len(facts.rankings)} keywords during {report_month}. "
                f"Of these, {imp} improved, {drp} dropped, "
                f"and {nf} were not found in search results. "
                "Refer to the detailed sections below for per-keyword analysis and recommendations."
            )
            logger.info("Using fallback narrative (LLM unavailable)")

        # ── 6. Generate output ──
        if output_format == "ppt":
            from report.ppt import build_ppt
            from report.report_agents import ReportMakerAgent, ReportReviewerAgent
            maker = ReportMakerAgent(self.groq)
            reviewer = ReportReviewerAgent(self.groq)

            section_narratives = maker.run(facts, narrative)
            logger.info(f"Maker generated {len(section_narratives)} section narratives")

            output_bytes = build_ppt(
                facts=facts,
                narrative=narrative,
                narratives=section_narratives,
                chart_images=chart_images,
                screenshots=screenshots,
                psi_screenshots=psi_screenshots,
            )

            MAX_REVIEW_ITERATIONS = 2
            for iteration in range(MAX_REVIEW_ITERATIONS):
                review = reviewer.review(output_bytes)
                logger.info(
                    f"Review iteration {iteration + 1}: score={review.get('score')} "
                    f"approved={review.get('approved')} "
                    f"issues={len(review.get('issues', []))}"
                )
                if review.get("approved"):
                    logger.info("Review PASSED — report is client-ready")
                    break
                if iteration < MAX_REVIEW_ITERATIONS - 1:
                    logger.warning("Review FAILED — rebuilding with revision notes")
                    revised_narrative = (
                        f"{narrative}\n\nRevision notes:\n"
                        + "\n".join(review.get("issues", []))
                    )
                    section_narratives = maker.run(facts, revised_narrative)
                    output_bytes = build_ppt(
                        facts=facts,
                        narrative=revised_narrative,
                        narratives=section_narratives,
                        chart_images=chart_images,
                        screenshots=screenshots,
                        psi_screenshots=psi_screenshots,
                    )
                else:
                    logger.warning("Max review iterations reached, delivering as-is")

            # ── 7. Action plan (internal team document) ──
            try:
                from report.action_plan_doc import build_action_plan_doc
                ap_blob = build_action_plan_doc(
                    facts=facts,
                    agency=self.agency_name,
                    client=self.client_name,
                    month=report_month,
                )
                ap_base = f"{self.client_name.replace(' ', '_')}_{report_month.replace(' ', '_')}_Action_Plan"
                ap_name = f"{ap_base}.pptx"
                ap_path = os.path.join(self.output_dir, ap_name)
                for ap_attempt in range(3):
                    try:
                        with open(ap_path, "wb") as f:
                            f.write(ap_blob)
                        break
                    except PermissionError:
                        if ap_attempt < 2:
                            ap_name = f"{ap_base}_{int(time.time())}.pptx"
                            ap_path = os.path.join(self.output_dir, ap_name)
                        else:
                            raise
                logger.info(f"Action plan saved: {ap_path} ({len(ap_blob) // 1024} KB)")
            except Exception as e:
                logger.warning("Action plan generation failed: %s", e)

            ext = "pptx"
        else:
            rankings_dicts = [
                {
                    "Keyword": r.keyword,
                    "Target URL": r.target_url,
                    "Position": str(r.position.value) if r.position.is_available else "",
                    "Change": str(r.change.value) if r.change.is_available else "",
                    "Data Availability": str(r.data_availability.value) if r.data_availability.is_available else "",
                }
                for r in facts.rankings
            ]
            audit_dicts = [
                {
                    "URL": iss.page,
                    "Issues": iss.issue_text,
                    "Images Missing Alt": 0,
                    "Word Count": 0,
                    "Has HTTPS": "Yes",
                }
                for iss in facts.technical.issues_list
            ]
            ai_dicts = [
                {
                    "Keyword": r.keyword,
                    "Observed Change": str(r.change.value) if r.change.is_available else "",
                    "Likely Cause": "",
                    "Recommendation": "",
                    "Priority": "",
                }
                for r in facts.rankings[:10]
            ]
            output_bytes = build_pdf(
                agency_name=self.agency_name,
                report_month=report_month,
                client_name=self.client_name,
                rankings=rankings_dicts,
                history_records=history_raw,
                ai_analyses=ai_dicts,
                audit_records=audit_dicts,
                insights=[{"URL": "", "Desktop PSI": "", "Mobile PSI": "", "BrowserOS Load Time": ""}],
                plan_items=[{"Item": a.task, "Priority": a.priority, "Section": "General"} for a in facts.action_plan],
                competitor_records=competitor_raw,
                narrative=narrative,
                chart_images=chart_images,
                screenshots=screenshots,
            )
            ext = "pdf"

        base_name = f"{self.client_name.replace(' ', '_')}_{report_month.replace(' ', '_')}_Monthly_Report"
        filename = f"{base_name}.{ext}"
        filepath = os.path.join(self.output_dir, filename)
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with open(filepath, "wb") as f:
                    f.write(output_bytes)
                break
            except PermissionError:
                if attempt < max_attempts - 1:
                    filename = f"{base_name}_{int(time.time())}.{ext}"
                    filepath = os.path.join(self.output_dir, filename)
                else:
                    raise

        logger.info(f"{ext.upper()} saved: {filepath} ({len(output_bytes) // 1024} KB)")
        return filepath
