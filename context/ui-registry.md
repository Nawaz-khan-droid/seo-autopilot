# UI Registry

Living document. Updated after every component is built. Read this before building any new component — match existing patterns exactly before inventing new ones.

---

## How to Use

Before building any component:

1. Check if a similar component already exists here
2. If yes — match its exact classes and structure
3. If no — build it following ui-rules.md and ui-tokens.md, then add it here

After building any component — update this file with the component name, file path, and exact styling used.

---

## Components

### Frontend (seo-report-frontend/)

| Component        | File                  | Description                                      | Key Classes / Styling                           |
| ---------------- | --------------------- | ------------------------------------------------ | ----------------------------------------------- |
| Navbar           | `index.html`          | Top navigation bar with Home, Generate, API Docs | `nav` flex, white bg, shadow-sm, h-64px         |
| Hero Section     | `index.html`          | Landing hero with title, subtitle, CTA buttons   | `section`, gradient bg option, max-w-1200px     |
| Client Select    | `index.html`          | Dropdown for selecting report client             | `select` styled input, border, md border-radius  |
| Report Preview   | `js/app.js`           | Accordion-style mock report sections             | Collapsible cards, toggle arrow, full-width     |
| Action Plan Preview | `js/app.js`         | Accordion-style mock action plan sections        | Same pattern as Report Preview                  |
| API Docs Section | `index.html`          | Endpoint reference with curl/js code examples    | Code blocks with copy button, table layout      |
| Feature Cards    | `index.html`          | Three-column feature overview on landing         | Card grid, icon + title + description           |
| Download Button  | `index.html`          | Primary CTA for downloading reports              | Navy bg, white text, md border-radius, disabled state |

### DOCX Components (report/)

| Component            | File                  | Description                                      | Layout Pattern                                 |
| -------------------- | --------------------- | ------------------------------------------------ | ---------------------------------------------- |
| Cover Card           | `docx_report.py`      | Report cover with agency, client, period         | NAVY full-width row, white text, 18pt title    |
| Executive Dashboard  | `docx_report.py`      | KPI snapshot with comparison arrows and insights | Grey label row + white value row table         |
| GSC Performance      | `docx_report.py`      | Clicks/impressions comparison                    | Two-column table + explanatory bullets         |
| Search Visibility    | `docx_report.py`      | Keyword distribution chart + table               | Chart row + ranking table                      |
| Top Keywords         | `docx_report.py`      | Winners with gain analysis                       | Keyword table with green gain badges           |
| Keywords Needing Attention | `docx_report.py` | Losers with recovery actions                     | Keyword table with amber loss badges           |
| Press Coverage       | `docx_report.py`      | Media rankings table                             | Source + position + URL table                  |
| Local SEO GMB        | `docx_report.py`      | GMB keyword tracking + observations              | GMB keyword table + observation bullets         |
| Off-Page Activities  | `docx_report.py`      | Bookmarking, image/video submissions             | Categorised list tables                        |
| SEO Activities       | `docx_report.py`      | All tasks categorised with status                | Activity table with status column              |
| Core Web Vitals      | `docx_report.py`      | Mobile/desktop scores + optimisation             | Score row + abstract improvement bullets       |
| Technical SEO        | `docx_report.py`      | Audit results + issues severity table            | Issues table with SEVERITY badges              |
| Recommendations      | `docx_report.py`      | Priority breakdown P0–P2                         | Priority rows with effort/impact columns       |
| Action Plan by Team  | `docx_report.py`      | Team assignments with priorities                 | Team-sectioned table                           |
| Summary & Next Steps | `docx_report.py`      | Key priorities for next period                   | Bullet list + closing statement                |

### DOCX Components (Action Plan)

| Component            | File                       | Description                                      | Layout Pattern                                 |
| -------------------- | -------------------------- | ------------------------------------------------ | ---------------------------------------------- |
| Cover Card           | `docx_action_plan.py`      | Action plan cover (same style as report)         | NAVY full-width row, white text                |
| Task Landscape       | `docx_action_plan.py`      | Summary of all tasks by team and priority        | Summary table with counts                      |
| SEO Team Tasks       | `docx_action_plan.py`      | SEO action items with details                    | Action item table with priority, effort, ETA   |
| Dev Team Tasks       | `docx_action_plan.py`      | Dev action items with technical specs            | Action item table                              |
| Content Team Tasks   | `docx_action_plan.py`      | Content production tasks                         | Action item table                              |
| Local/Off-Page Tasks | `docx_action_plan.py`      | Local SEO + outreach tasks                       | Action item table                              |
| Priority Matrix      | `docx_action_plan.py`      | P0–P3 breakdown by effort/impact                 | Priority grid table                            |
| Technical Specs      | `docx_action_plan.py`      | Raw CWV metrics (LCP, INP, CLS)                  | Metric name + value + target + status table    |
| Advisor Summary      | `docx_action_plan.py`      | Strategic notes + recommendations                | Paragraph + bullet list                        |

---

## Patterns to Match

### DOCX Table Pattern

```
Header row: NAVY background, WHITE text, 9pt, bold
Data rows: 9pt body text, alternating shading
Severity cells: coloured background fill (RED/AMBER/ACCENT/GRAY)
Table width: 100% of page
```

### DOCX Section Pattern

```
Page break (new card)
Full-width header row: NAVY background, WHITE text, 18pt title
Content area: paragraphs, tables, bullets
Explanatory section: Grey label "What this means for your business" + bullet list
```

### Frontend Card Pattern

```
White background, 16px border radius, 1px border #E2E8F0
24px padding, subtle box-shadow
Title at top (18px, 600 weight)
Content below (15px body text)
```

### Frontend Section Pattern

```
Section heading (24px, 600 weight)
Card(s) with content
32px gap between sections
```
