"""Professional PDF report builder — covers, cards, tables, charts, screenshots."""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle, Image,
)

# ── Colour palette ──
C_DARK = colors.HexColor("#0a0e0f")
C_DARK2 = colors.HexColor("#0d1214")
C_GREEN = colors.HexColor("#00c98a")
C_AMBER = colors.HexColor("#f5c842")
C_LIGHT = colors.HexColor("#d0dde3")
C_MID = colors.HexColor("#4a6570")
C_ROW1 = colors.HexColor("#f4f7f8")
C_GRID = colors.HexColor("#dde4e7")
C_RED = colors.HexColor("#d94040")
C_WHITE = colors.white

MARGIN = 18 * mm
PW = A4[0] - 2 * MARGIN  # page usable width


def _ps(name, **kw):
    return ParagraphStyle(name, **kw)


# ── Paragraph styles ──
st_cv_title = _ps("cv_t", fontName="Helvetica-Bold", fontSize=26, textColor=C_WHITE, leading=32, alignment=TA_LEFT)
st_cv_sub = _ps("cv_s", fontName="Helvetica", fontSize=12, textColor=C_GREEN, leading=16, alignment=TA_LEFT)
st_cv_meta = _ps("cv_m", fontName="Helvetica", fontSize=9, textColor=C_LIGHT, leading=12, alignment=TA_LEFT)
st_sec = _ps("sec", fontName="Helvetica-Bold", fontSize=13, textColor=C_DARK, spaceBefore=10, spaceAfter=4)
st_sub = _ps("sub", fontName="Helvetica-Bold", fontSize=9.5, textColor=C_MID, spaceBefore=6, spaceAfter=3)
st_bul = _ps("bul", fontName="Helvetica", fontSize=8.5, textColor=C_DARK, leading=12, leftIndent=10, spaceAfter=2)
st_bul_s = _ps("buls", fontName="Helvetica", fontSize=8, textColor=C_MID, leading=11, leftIndent=14, spaceAfter=1.5)
st_body = _ps("body", fontName="Helvetica", fontSize=8.5, textColor=C_DARK, leading=12, spaceAfter=3)
st_lab = _ps("lab", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE, leading=11, alignment=TA_CENTER)
st_val = _ps("val", fontName="Helvetica-Bold", fontSize=16, textColor=C_GREEN, leading=20, alignment=TA_CENTER)
st_hdr = _ps("hdr", fontName="Helvetica-Bold", fontSize=7.5, textColor=C_GREEN, leading=9.5)
st_cell = _ps("cel", fontName="Helvetica", fontSize=7.5, textColor=C_DARK, leading=9.5)
st_ftr = _ps("ftr", fontName="Helvetica", fontSize=6.5, textColor=C_LIGHT, alignment=TA_CENTER)


# ── Helpers ──
def _dark(rows, bg=C_DARK, pt=20, pb=20):
    t = Table(rows, colWidths=[PW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (0, 0), pt),
        ("BOTTOMPADDING", (0, -1), (-1, -1), pb),
        ("TOPPADDING", (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
    ]))
    return t


def _card(data, cw):
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
        ("BACKGROUND", (0, 1), (-1, 1), C_DARK2),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, C_MID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def _table(data, widths):
    t = Table(data, colWidths=widths, repeatRows=1)
    s = [
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_GREEN),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_ROW1, C_WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.4, C_GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    t.setStyle(TableStyle(s))
    return t


def _clr(v):
    v = str(v).strip()
    if v.startswith("+"):
        return Paragraph(f'<font color="{C_GREEN.hexval()}"><b>{v}</b></font>', st_cell)
    if v.startswith("-"):
        return Paragraph(f'<font color="{C_RED.hexval()}"><b>{v}</b></font>', st_cell)
    return Paragraph(v, st_cell)


def _badge(text, top3=("1", "2", "3")):
    t = text.strip().lower()
    if t in top3:
        c = C_GREEN
    elif t in ("not found", "no", "n/a", "error"):
        c = C_RED
    else:
        c = C_AMBER
    return Paragraph(f'<font color="{c.hexval()}"><b>{text}</b></font>', st_cell)


def _bul(text, sub=False):
    return Paragraph(f"\u2022  {text}", st_bul_s if sub else st_bul)


# ── Main builder ──
def build_pdf(agency_name, report_month, client_name,
              rankings, history_records, ai_analyses,
              audit_records, insights, plan_items,
              competitor_records, narrative, chart_images,
              screenshots=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=14 * mm, bottomMargin=14 * mm)
    story = []

    # ═══════════════════════════════════════════════════════════════
    # PAGE 1 — COVER
    # ═══════════════════════════════════════════════════════════════
    story.append(_dark([[Paragraph(agency_name, st_cv_title)]], pt=40, pb=10))
    story.append(_dark([
        [Paragraph("Monthly SEO Performance Report", st_cv_sub)],
        [Paragraph(report_month, st_cv_meta)],
        [Paragraph(f"Client: {client_name}", st_cv_meta)],
        [Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y')}", st_cv_meta)],
    ], bg=C_DARK2, pt=12, pb=30))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # PAGE 2 — EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════════
    story.append(Paragraph("Executive Summary", st_sec))
    story.append(HRFlowable(width=PW, thickness=1, color=C_GREEN, spaceAfter=6))

    improved = sum(1 for r in rankings if str(r.get("Change", "")).startswith("+"))
    dropped = sum(1 for r in rankings if str(r.get("Change", "")).startswith("-"))
    stable = sum(1 for r in rankings if str(r.get("Position", "")).strip().lower()
                 not in ("not found", "") and str(r.get("Change", "")).strip() in ("0", ""))
    not_found = sum(1 for r in rankings if str(r.get("Position", "")).strip().lower() == "not found")
    total = len(rankings) or 1

    cw5 = PW / 5
    story.append(_card([
        [Paragraph("Tracked", st_lab), Paragraph("Improved", st_lab),
         Paragraph("Dropped", st_lab), Paragraph("Stable", st_lab),
         Paragraph("Not Found", st_lab)],
        [Paragraph(str(total), st_val), Paragraph(str(improved), st_val),
         Paragraph(str(dropped), st_val), Paragraph(str(stable), st_val),
         Paragraph(str(not_found), st_val)],
    ], [cw5] * 5))

    # Bullet summary
    if narrative:
        story.append(Spacer(1, 8))
        for line in narrative.strip().split("\n"):
            c = line.strip().lstrip("*").lstrip("-").strip()
            if not c or len(c) < 8:
                continue
            story.append(_bul(c[:280]))

    # Wins / Drops
    wins = [r for r in rankings if str(r.get("Change", "")).startswith("+")]
    drops = [r for r in rankings if str(r.get("Change", "")).startswith("-")]
    nf = [r for r in rankings if str(r.get("Position", "")).strip().lower() == "not found"]

    story.append(Spacer(1, 8))
    if wins:
        story.append(Paragraph("<b>Key Wins</b>", st_sub))
        for w in wins[:3]:
            story.append(_bul(f'<b>{w["Keyword"]}</b> \u2192 #{w["Position"]} ({w["Change"]})'))
    if drops:
        story.append(Paragraph("<b>Needs Attention</b>", st_sub))
        for d in drops[:3]:
            p = f'#{d["Position"]}' if d["Position"].strip().lower() != "not found" else "Not Found"
            story.append(_bul(f'<b>{d["Keyword"]}</b> \u2192 {p} ({d["Change"]})'))
    if nf:
        story.append(Paragraph("<b>Not Ranking</b>", st_sub))
        for r in nf[:3]:
            story.append(_bul(f'<b>{r["Keyword"]}</b> \u2014 not found in top 50'))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # PAGE 3 — KEYWORD RANKINGS + CHARTS
    # ═══════════════════════════════════════════════════════════════
    story.append(Paragraph("Keyword Rankings", st_sec))
    story.append(HRFlowable(width=PW, thickness=1, color=C_GREEN, spaceAfter=6))

    if rankings:
        kw_data = [["Keyword", "Position", "Change", "Source"]] + [
            [r.get("Keyword", "-"),
             _badge(str(r.get("Position", "-"))),
             _clr(r.get("Change", "-")),
             r.get("Data Availability", "-")]
            for r in rankings
        ]
        story.append(_table(kw_data, [PW * 0.40, PW * 0.14, PW * 0.14, PW * 0.32]))
    story.append(Spacer(1, 8))

    # Charts
    if chart_images:
        story.append(Paragraph("Ranking Trends", st_sub))
        ch = list(chart_images.keys())
        for i in range(0, len(ch), 2):
            row = []
            cw = []
            for j in range(2):
                if i + j < len(ch):
                    kw = ch[i + j]
                    img = Image(io.BytesIO(chart_images[kw]),
                                width=PW / 2 - 4, height=PW / 4.5)
                    row.append(img)
                    cw.append(PW / 2 - 4)
            if row:
                rt = Table([row], colWidths=cw)
                rt.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]))
                story.append(rt)
                story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # PAGE 4 — SCREENSHOTS (visual proof)
    # ═══════════════════════════════════════════════════════════════
    has_shots = screenshots and any(
        s.get("desktop_png") or s.get("mobile_png")
        for s in screenshots.values()
    )
    if has_shots:
        story.append(Paragraph("Page Visual Preview", st_sec))
        story.append(HRFlowable(width=PW, thickness=1, color=C_GREEN, spaceAfter=6))

        for kw, shots in screenshots.items():
            desktop = shots.get("desktop_png")
            mobile = shots.get("mobile_png")
            if not desktop and not mobile:
                continue

            story.append(Paragraph(f"<b>{kw}</b>", st_sub))

            if desktop and mobile:
                img_d = Image(io.BytesIO(desktop), width=PW * 0.60, height=PW * 0.38)
                img_m = Image(io.BytesIO(mobile), width=PW * 0.32, height=PW * 0.50)
                rt = Table([[img_d, img_m]], colWidths=[PW * 0.60, PW * 0.40])
                rt.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]))
                story.append(rt)
            elif desktop:
                img = Image(io.BytesIO(desktop), width=PW, height=PW * 0.60)
                story.append(img)
            elif mobile:
                img = Image(io.BytesIO(mobile), width=PW * 0.35, height=PW * 0.55)
                story.append(img)

            story.append(Spacer(1, 8))

        story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # PAGE 5 — KEY ACTIONS & RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════════
    story.append(Paragraph("Key Actions &amp; Recommendations", st_sec))
    story.append(HRFlowable(width=PW, thickness=1, color=C_GREEN, spaceAfter=6))

    valid = [a for a in ai_analyses
             if "historical context unavailable" not in str(a.get("Likely Cause", "")).lower()
             and "historical context unavailable" not in str(a.get("Observed Change", "")).lower()]

    if valid:
        for analysis in valid:
            kw = analysis.get("Keyword", "?")
            change = str(analysis.get("Observed Change", "") or "").strip()
            cause = str(analysis.get("Likely Cause", "") or "").strip()
            rec = str(analysis.get("Recommendation", "") or "").strip()
            priority = str(analysis.get("Priority", "") or "").strip()

            pcol = C_GREEN if priority.lower() == "high" else (C_AMBER if priority.lower() == "medium" else C_MID)
            tag = f'  <font color="{pcol.hexval()}">[{priority}]</font>' if priority else ""
            story.append(Paragraph(f"<b>{kw}</b>{tag}", st_sub))
            if change:
                story.append(_bul(change[:220]))
            if cause:
                story.append(_bul(f"<i>Root cause:</i> {cause[:220]}", sub=True))
            if rec:
                story.append(_bul(f"<b>Suggested action:</b> {rec[:220]}", sub=True))
            story.append(Spacer(1, 2))
    else:
        story.append(Paragraph("Analysis data will appear after the next tracking run.", st_body))

    story.append(Spacer(1, 8))

    # Monthly action plan
    if plan_items:
        story.append(Paragraph("Action Plan for Next Month", st_sec))
        story.append(HRFlowable(width=PW, thickness=1, color=C_GREEN, spaceAfter=6))

        sections = {}
        for item in plan_items:
            sec = str(item.get("Section", "General") or "General")
            sections.setdefault(sec, []).append(item)

        for sn in ["CRITICAL ACTIONS", "KEYWORD PRIORITIES", "TECHNICAL FIXES",
                    "CONTENT GAPS", "TIMELINE", "General"]:
            items = sections.pop(sn, [])
            if not items:
                continue
            story.append(Paragraph(sn, st_sub))
            for item in items:
                d = str(item.get("Details", "") or item.get("Item", "") or "")
                p = str(item.get("Priority", "") or "")
                pt = f' <font color="{C_AMBER.hexval()}">[{p}]</font>' if p else ""
                story.append(_bul(f"{d}{pt}"))
            story.append(Spacer(1, 3))

        for sn, items in sections.items():
            if items:
                story.append(Paragraph(sn, st_sub))
                for item in items:
                    story.append(_bul(item.get("Details", item.get("Item", ""))))
                story.append(Spacer(1, 3))

    # ═══════════════════════════════════════════════════════════════
    # PAGE 6 — TECHNICAL AUDIT
    # ═══════════════════════════════════════════════════════════════
    if audit_records:
        story.append(PageBreak())
        story.append(Paragraph("Technical Audit Summary", st_sec))
        story.append(HRFlowable(width=PW, thickness=1, color=C_AMBER, spaceAfter=6))

        asum = {"pages": len(audit_records), "issues": 0, "missing_alt": 0, "thin": 0}
        top_issues = []
        for r in audit_records:
            iss = str(r.get("Issues", "") or "")
            if iss and iss != "None":
                n = len(iss.split(";"))
                asum["issues"] += n
                for i in iss.split(";"):
                    i = i.strip()
                    if i and i not in top_issues:
                        top_issues.append(i)
            try:
                asum["missing_alt"] += int(r.get("Images Missing Alt", 0) or 0)
            except (ValueError, TypeError):
                pass
            try:
                wc = int(r.get("Word Count", 0) or 0)
                if 0 < wc < 300:
                    asum["thin"] += 1
            except (ValueError, TypeError):
                pass

        cw4 = PW / 4
        story.append(_card([
            [Paragraph("Pages", st_lab), Paragraph("Issues", st_lab),
             Paragraph("Alt Missing", st_lab), Paragraph("Thin Pages", st_lab)],
            [Paragraph(str(asum["pages"]), st_val), Paragraph(str(asum["issues"]), st_val),
             Paragraph(str(asum["missing_alt"]), st_val), Paragraph(str(asum["thin"]), st_val)],
        ], [cw4] * 4))

        if top_issues:
            story.append(Spacer(1, 4))
            story.append(Paragraph("Key Issues", st_sub))
            for iss in top_issues[:6]:
                story.append(_bul(iss[:120]))

        story.append(Spacer(1, 6))
        adata = [["Page", "Words", "Issues", "Alt", "HTTPS"]] + [
            [r.get("URL", "-").split("/")[-1][:25] or r.get("URL", "-")[:25],
             str(r.get("Word Count", "-")),
             str(r.get("Issues", "-"))[:45],
             str(r.get("Images Missing Alt", "0")),
             _badge(r.get("Has HTTPS", "-"), top3=("yes", "y", "true"))]
            for r in audit_records
        ]
        story.append(_table(adata, [PW * 0.28, PW * 0.10, PW * 0.32, PW * 0.10, PW * 0.20]))

    # ═══════════════════════════════════════════════════════════════
    # PAGE 7 — PAGE SPEED + COMPETITORS
    # ═══════════════════════════════════════════════════════════════
    if insights or competitor_records:
        if not audit_records:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 10))

    if insights:
        story.append(Paragraph("Page Speed Overview", st_sec))
        story.append(HRFlowable(width=PW, thickness=1, color=C_GREEN, spaceAfter=6))
        idata = [["URL", "Desktop", "Mobile", "Load Time"]] + [
            [r.get("URL", "-").split("/")[-1][:25] or r.get("URL", "-")[:25],
             str(r.get("Desktop PSI", "N/A")),
             str(r.get("Mobile PSI", "N/A")),
             str(r.get("BrowserOS Load Time", "N/A"))]
            for r in insights
        ]
        story.append(_table(idata, [PW * 0.30, PW * 0.20, PW * 0.20, PW * 0.30]))
        story.append(Spacer(1, 10))

    if competitor_records:
        story.append(Paragraph("Competitor Landscape", st_sec))
        story.append(HRFlowable(width=PW, thickness=1, color=C_GREEN, spaceAfter=6))
        cdata = [["Keyword", "Competitor 1", "Competitor 2", "Competitor 3"]] + [
            [r.get("Keyword", "-"),
             r["Top 1"].split("/")[2][:25] if "//" in str(r.get("Top 1", "")) else r.get("Top 1", "-"),
             r["Top 2"].split("/")[2][:25] if "//" in str(r.get("Top 2", "")) else r.get("Top 2", "-"),
             r["Top 3"].split("/")[2][:25] if "//" in str(r.get("Top 3", "")) else r.get("Top 3", "-")]
            for r in competitor_records
        ]
        story.append(_table(cdata, [PW * 0.22, PW * 0.26, PW * 0.26, PW * 0.26]))

    # ═══════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 16))
    ft = Table([
        [Paragraph(f"{agency_name}  |  {report_month}  |  Automated SEO Report", st_ftr)]
    ], colWidths=[PW])
    ft.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(ft)

    doc.build(story)
    return buf.getvalue()
