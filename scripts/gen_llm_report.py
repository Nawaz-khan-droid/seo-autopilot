"""Generate an LLM-powered SEO report — markdown + HTML.

Uses Groq (Llama 3 70B) to write a rich, executive-ready report
from structured ReportFacts data. No python-pptx shape-painting.
"""
import sys, os, io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import GROQ_API_KEY, GROQ_MODEL
from modules.groq_client import GroqClient
from report.facts import ReportFacts, RankingRow, Kpidata, CWVData
from report.facts import TechnicalData, MonthlyTrafficPoint, ActionItem, TechnicalIssue, GMBKeywordRow, LocalSEOData
from report.evidence import Evidence
from report.llm_report_generator import generate_markdown_report, markdown_to_html
from report.docx_report import build_clients_report
from report.docx_action_plan import build_action_plan_docx
from report.client_context import get_client_keywords, get_client_context, build_context_prompt_section


def build_sample_facts() -> ReportFacts:
    """Build sample data using Beautiful India's real product keywords."""
    f = ReportFacts()
    f.metadata.client_name = "Beautiful India"
    f.metadata.agency_name = "Apex Digital Agency"
    f.metadata.report_month = "June 2026"
    f.metadata.generated_at = "2026-06-10T14:00:00"

    kw_data = get_client_keywords("beautiful india")
    for kw, pos, chg in kw_data:
        prev = str(max(1, int(pos) - int(chg)))
        f.rankings.append(RankingRow(
            keyword=kw,
            target_url="https://www.beautifulindia.com/" + kw.replace(" ", "-"),
            position=Evidence.verified(pos, "SERP Snapshot"),
            change=Evidence.verified(chg, "SERP History"),
            data_availability=Evidence.verified("Found", "SERP Snapshot"),
            competition="informational",
            previous_position=Evidence.verified(prev, "History"),
        ))
    # Assign realistic search intent
    f.rankings[0].competition = "commercial"   # beautiful india perfume
    f.rankings[2].competition = "navigational" # beautiful india one perfume
    f.rankings[4].competition = "commercial"   # beautiful india discovery set
    f.rankings[10].competition = "transactional" # luxury fragrance india

    f.kpis = Kpidata(
        clicks=Evidence.verified("430", "GSC"),
        impressions=Evidence.verified("25.3K", "GSC"),
        clicks_change=Evidence.verified("-86", "GSC MoM"),
        impressions_change=Evidence.verified("+2.6K", "GSC MoM"),
        organic_users=Evidence.missing(),
        organic_users_change=Evidence.missing(),
        engaged_sessions=Evidence.missing(),
        engaged_sessions_change=Evidence.missing(),
        avg_engagement_time=Evidence.missing(),
        monthly_traffic=[],
    )

    f.technical = TechnicalData(
        health_score=Evidence.verified(76, "Site Audit"),
        pages_audited=Evidence.verified(24, "Site Audit"),
        total_issues=Evidence.verified(31, "Site Audit"),
        missing_h1=Evidence.verified(5, "Site Audit"),
        missing_meta=Evidence.verified(7, "Site Audit"),
        missing_alt=Evidence.verified(38, "Site Audit"),
        thin_pages=Evidence.verified(3, "Site Audit"),
    )
    f.technical.issues_list = [
        TechnicalIssue(severity="Critical", page="/perfume-one.html", issue_text="Missing canonical tag on product page"),
        TechnicalIssue(severity="Critical", page="/about", issue_text="Duplicate title tag"),
        TechnicalIssue(severity="High", page="/blog", issue_text="Slow page load (4.2s)"),
        TechnicalIssue(severity="Medium", page="/contact", issue_text="Missing meta description"),
    ]

    f.cwv = CWVData(
        mobile_score=Evidence.verified(62, "PageSpeed API"),
        desktop_score=Evidence.verified(91, "PageSpeed API"),
        lcp_seconds=Evidence.verified(3.8, "PageSpeed API"),
        inp_ms=Evidence.verified(210, "PageSpeed API"),
        cls_score=Evidence.verified(0.08, "PageSpeed API"),
        render_blocking_ms=Evidence.verified(920, "PageSpeed API"),
    )

    # AI Overview data — only included if actually verified from SERP snapshot
    # (currently no verified data, so omitting to prevent hallucination)

    # Add previous month positions for trend charts
    for r in f.rankings:
        cur = int(r.position.value) if r.position.value else 1
        chg = int(r.change.value) if r.change.value else 0
        prev = max(1, cur - chg)
        r.previous_position = Evidence.verified(str(prev), "History")

    # ── GMB Keywords (matching actual Beautiful India PDF) ──
    gmb_dates = ["31 May", "10 Jun", "20 Jun", "30 Jun"]
    gmb_data = [
        ("Luxury perfume shop in bandra",    ["1", "1", "5", "2"]),
        ("Luxury perfume store bandra",      ["1", "1", "1", "1"]),
        ("Luxury Perfume Stores",            ["11", "11", "13", "10"]),
        ("Luxury Perfume Stores in Bandra",  ["1", "1", "3", "3"]),
        ("Luxury Perfumes Near Me",          ["4", "6", "10", "5"]),
        ("Luxury Perfume Shops in Bandra",   ["1", "1", "4", "3"]),
        ("Perfume in Bandra",                ["4", "5", "7", "5"]),
        ("Luxury perfume in India",          ["3", "4", "5", "4"]),
        ("Luxury perfume in Mumbai",         ["6", "11", "15", "9"]),
        ("Luxury candles in Mumbai",         ["13", "12", "11", "11"]),
    ]
    for kw, pos in gmb_data:
        f.gmb_keywords.append(GMBKeywordRow(keyword=kw, dates=gmb_dates, positions=pos))

    # ── Press Coverage (matching PDF) ──
    f.press_coverages = [
        "Beautiful India in Forbes \u2014 #1 on Google",
        "Beautiful India in Vogue \u2014 #1 on Google",
        "Beautiful India in Cond\u00e9 Nast Traveler \u2014 #1 on Google",
        "Beautiful India in Grazia \u2014 #1 on Google",
        "Beautiful India in Cosmopolitan \u2014 #1 on Google",
        "Beautiful India in GQ \u2014 #1 on Google",
        "Beautiful India in the News \u2014 #1 on Google",
    ]

    # ── Off-page activities (matching PDF) ──
    f.social_bookmarks = [
        ("elitebizlisting.com", "Objects of Desire — India Today", "https://bookmarking.elitebizlisting.com/news/objects-of-desire"),
        ("instapaper.com", "Luxe desk staples — Harpers Bazaar", "https://www.instapaper.com/read/1834164956"),
        ("tumblr.com", "Standout Indie Beauty Labels — Grazia India", "https://brandbeautifulindia.tumblr.com/..."),
        ("scoop.it", "Celeb-Approved Perfumes — Fragrance Day", "https://sco.lt/8DfGwC"),
        ("getpocket.com", "Luxury Scents Gen Z Swear By — Times Now", "https://pocket.co/share/..."),
    ]
    f.image_submissions = [
        ("pinterest.com", "Print — INDULGE: New Indian Express", "https://pin.it/2ang59ewv"),
        ("justpaste.it", "Hasina Jeelani — BEAUTIFUL INDIA", "https://jpst.it/4q8tT"),
        ("tumblr.com", "Namrata Kedar — BEAUTIFUL INDIA", "https://brandbeautifulindia.tumblr.com/..."),
        ("shutterfly.com", "Payel Majumdar — Google Drive", "https://link.shutterfly.com/..."),
        ("gravatar.com", "Pratishtha Dobhal — BEAUTIFUL INDIA", "https://1.gravatar.com/..."),
    ]
    f.video_submissions = [
        ("dailymotion.com", "Hasina Jeelani — BEAUTIFUL INDIA", "https://dai.ly/k6BsEfxMz3trZ3DkFVK"),
        ("rumble.com", "Chumki Bhardwaj — Elegance in Every Drop", "https://rumble.com/v6vfwfj..."),
        ("tumblr.com", "Surina Sayal — BEAUTIFUL INDIA", "https://brandbeautifulindia.tumblr.com/..."),
    ]

    # ── Local SEO / GMB data ──
    f.local_seo = LocalSEOData(
        review_count=Evidence.verified("32", "GMB Profile"),
        avg_rating=Evidence.verified("4.7", "GMB Profile"),
        gmb_posts=Evidence.verified("4", "GMB Content Log"),
        gmb_observations=[
            "NA keywords are now getting positions on Google Maps.",
            "GMB profile visible on 19+ targeted keywords, enhancing local discoverability.",
            "8+ keywords have improved ranking this period.",
            "GMB profile ranks on 15+ keywords on Google's 1st page.",
        ],
        gmb_content_note="As of June 30, 2026, 4 GMB content posts published. Posts are actively enhancing online presence and driving engagement.",
    )

    # ── SEO Activities Completed (matching PDF structure) ──
    f.seo_activities_completed = [
        "Link Building on High DA PA Guest Posting websites",
        "Blog Topic Research & Blog Writing with keyword placement",
        "Blogger Outreach for Guest Posting opportunities",
        "Link Building via Web 2.0 Blog Posting",
        "Quora Answers with branded links",
        "Social Bookmarking on 5 high-authority platforms",
        "Image Submissions on 5 platforms",
        "Video Submissions on 3 platforms",
        "Ads Submission & PPT/PDF Submissions",
        "Image Schema Creation",
        "Article Promotion across online publications",
        "GMB Content Creation & Posting (4 posts)",
        "Added Contact Number to GMB Profile",
        "Web 2.0 Blogs Creation & Posting (Medium, Blogger, Tumblr)",
    ]

    # ── Way Forward (matching PDF) ──
    f.way_forward = [
        "Technical SEO Check & Error Fixing",
        "Guest Posting on high-authority domains",
        "Web 2.0 Blogs Posting & optimization",
        "Link Insertion in existing published blogs",
        "SEO Audit & Competitive Analysis",
        "Backlink Analysis & Backlink Building",
        "On-page optimization as needed",
        "GMB Content Posting & GMB Link Building",
        "Blog Creation & Social Bookmarking",
        "Target further articles for Beautiful India press coverage",
    ]

    # ── Action Plan (incl Off-Page team) ──
    teams = ["SEO", "Dev", "Content", "Local", "Off-Page"]
    tasks = [
        ("Fix missing canonical tags on product pages", "P0", "SEO Lead", "SEO", "Week 1"),
        ("Optimize mobile LCP (target <2.5s)", "P0", "Dev Lead", "Dev", "Week 1"),
        ("Recover dropped keyword content", "P1", "Content Strategist", "Content", "Week 2"),
        ("Respond to GMB reviews and update NAP", "P1", "Local SEO Specialist", "Local", "Week 1"),
        ("Guest post outreach — 5 new domains", "P1", "Off-Page Lead", "Off-Page", "Week 2"),
        ("Fix duplicate title tags", "P1", "SEO Lead", "SEO", "Week 2"),
        ("Create supporting content for Discovery Set", "P2", "Content Strategist", "Content", "Week 3-4"),
        ("Web 2.0 blog posting — 3 new articles", "P2", "Off-Page Lead", "Off-Page", "Week 2"),
        ("GMB content post — weekly update", "P2", "Local SEO Specialist", "Local", "Weekly"),
        ("Improve meta descriptions (7 missing)", "P2", "SEO Lead", "SEO", "Week 3-4"),
        ("Social bookmarking — 5 platforms", "P3", "Off-Page Lead", "Off-Page", "Week 3-4"),
        ("Image/video submissions — 5 platforms", "P3", "Off-Page Lead", "Off-Page", "Week 3-4"),
        ("Reduce render-blocking resources", "P1", "Dev Lead", "Dev", "Week 2"),
        ("Alternative text for 38 images", "P2", "Content Strategist", "Content", "Week 3-4"),
        ("SEO audit and competitive analysis", "P2", "SEO Lead", "SEO", "Week 3-4"),
    ]
    for task, pri, owner, team, eta in tasks:
        f.action_plan.append(ActionItem(
            task=task,
            priority=pri,
            impact="high" if pri == "P0" else ("medium" if pri == "P1" else "low"),
            effort="3d" if pri == "P0" else ("2d" if pri == "P1" else "1d"),
            owner=owner,
            team=team,
            eta=eta,
        ))

    return f


def main():
    print("=" * 60)
    print("LLM-POWERED SEO REPORT GENERATOR")
    print("=" * 60)

    # Load data
    print("\nBuilding sample data...")
    facts = build_sample_facts()

    # Build executive narrative
    executive_narrative = (
        "Beautiful India improved rankings across key product-related keywords this period. "
        "The brand's signature 'One' perfume holds #1, while 'Peace' ranks #2. "
        "The Discovery Set saw the biggest gain (+4 positions) — strong interest in the entry-point product. "
        "All press coverage keywords (Forbes, Vogue, Cond\u00e9 Nast Traveler, Grazia, Cosmopolitan, GQ) maintain #1 on Google. "
        "GMB local visibility strengthened with 15+ keywords on page 1 and 8+ improving positions. "
        "14 off-page SEO activities completed including social bookmarking, image/video submissions, and link building. "
        "Core Web Vitals need attention on mobile (62/100). "
        "Two critical technical issues were found: missing canonical tags and duplicate title tags."
    )

    # Initialize Groq client
    print(f"Initializing Groq client (model: {GROQ_MODEL})...")
    groq = GroqClient(api_key=GROQ_API_KEY, model=GROQ_MODEL)

    # Generate markdown report
    print("Generating report via LLM (this takes ~15-30 seconds)...")
    md = generate_markdown_report(facts, groq, executive_narrative)

    # Save markdown
    os.makedirs("output", exist_ok=True)
    md_path = os.path.join("output", f"{facts.metadata.client_name.replace(' ', '_')}_{facts.metadata.report_month.replace(' ', '_')}_Report.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"\nMarkdown saved: {md_path} ({len(md)} chars)")

    # Save HTML
    html = markdown_to_html(md, f"Monthly SEO Report — {facts.metadata.client_name}")
    html_path = md_path.replace(".md", ".html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"HTML saved:    {html_path} ({len(html)} chars)")

    # Save DOCX — Client Report (12-14 slide cards, no trend charts, no unverified AI)
    safe_name = facts.metadata.client_name.replace(' ', '_')
    safe_month = facts.metadata.report_month.replace(' ', '_')
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join("output", f"{safe_name} Monthly SEO Report {safe_month} {ts}.docx")
    report_result = build_clients_report(facts, output_path=report_path)
    print(f"MONTHLY SEO REPORT: {report_result}")

    # Save DOCX — Action Plan (6-10 slide cards, internal team)
    plan_path = os.path.join("output", f"{safe_name} SEO Action Plan {safe_month} {ts}.docx")
    plan_result = build_action_plan_docx(facts, output_path=plan_path)
    print(f"SEO ACTION PLAN: {plan_result}")

    # Print preview
    print("\n" + "=" * 60)
    print("REPORT PREVIEW (first 2000 chars):")
    print("=" * 60)
    print(md[:2000])

    if len(md) > 2000:
        print(f"\n... ({len(md) - 2000} more characters)")


if __name__ == "__main__":
    main()
