# Library Docs

Project-specific usage patterns for every third party library in this project. This file only covers how we use each library in this specific project — rules, patterns, and constraints specific to SEO Autopilot.

---

## Before Using Any Library

Before implementing any feature that uses a third party library:

1. **Check if this is the correct tool** — Could you achieve the same with standard library tools? Only add dependencies when necessary.

2. **Check the approved dependencies list** in `code-standards.md` — only packages on that list are approved.

3. **Read this file** for project-specific patterns that override general library knowledge.

---

## python-docx

The primary document generation tool for both client reports and action plans.

### Project Pattern

All DOCX generation follows the same pattern established in `report/docx_report.py` and `report/docx_action_plan.py`. Every builder:

1. Creates a `Document()` instance
2. Builds sections using helper functions (`_para`, `_cell`, `_bullets`, `_shd`)
3. Saves to `BytesIO` and returns `bytes`

### Helper Functions (Shared Convention)

```python
# Fill cell background
def _shd(cell, color_hex: str):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}" w:val="clear"/>')
    cell._tc.get_or_add_tcPr().append(shading)

# Write text to a table cell
def _cell(cell, text, bold=False, color=None, size=10, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    r = p.add_run(text)
    r.bold = bold
    r.font.name = FN
    r.font.size = Pt(size)
    if color: r.font.color.rgb = color
    if align is not None: p.alignment = align

# Add a paragraph
def _para(doc, text, bold=False, color=None, size=10, align=None, before=0, after=0):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.font.name = FN
    r.font.size = Pt(size)
    if color: r.font.color.rgb = color
    if align is not None: p.alignment = align
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    return p

# Add bullet points
def _bullets(doc, items, size=10):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(1)
        r = p.add_run(item)
        r.font.size = Pt(size)
        r.font.name = FN

# Extract evidence value safely
def _ev(v):
    if v is None: return "\u2014"
    if hasattr(v, "is_available") and not v.is_available: return "\u2014"
    val = v.value if hasattr(v, "value") else v
    return str(val) if val is not None else "\u2014"
```

### Card Pattern (Client Report)

Each section follows this layout:

```
Page break
Full-width table (1 row, 1 col) — NAVY background, title text in WHITE
    → Section title like "Executive Dashboard"
Body content below (paragraphs, tables, bullets)
    → Explanatory bullet points at end of every section
```

### Card Pattern (Action Plan)

Same page-break + header approach, but:

- Team tables use striped row colours (NAVY headers, alternating WHITE/GRAY backgrounds)
- Severity column has coloured badges using `_shd()` with RED/AMBER/ACCENT/GRAY
- CWV section renders raw numbers (LCP in seconds, INP in ms, CLS score)
- Advisor Summary card has broader strategic language

### Table Construction

```python
# Full-width table with header
table = doc.add_table(rows=1, cols=3)
table.alignment = WD_TABLE_ALIGNMENT.CENTER

# Set column widths
for i, width in enumerate([Inches(2), Inches(3), Inches(1.5)]):
    table.columns[i].width = width

# Header row
_cell(table.rows[0].cells[0], "Header 1", bold=True, color=WHITE, size=9)
_shd(table.rows[0].cells[0], "0F2747")

# Data rows
for item in items:
    row = table.add_row()
    _cell(row.cells[0], item.field1, size=9)
    _cell(row.cells[1], item.field2, size=9)
```

**Rules:**

- Always stretch tables to 100% width
- Header row always NAVY background with WHITE text, 9pt
- Data rows 9pt body text
- Striped rows: alternating plain / light gray background
- Severity column uses colour-coded fill: Critical=RED, High=AMBER, Medium=ACCENT, Low=GRAY

### Chart Embedding

```python
# Generate chart image bytes
chart_buf = make_distribution_hbar_chart(items, title)
chart_buf.seek(0)

# Add inline to DOCX
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run()
run.add_picture(chart_buf, width=Inches(6), height=Inches(3))
```

Charts use matplotlib rendered to `BytesIO`, then embedded as inline PNG in the DOCX.

---

## matplotlib

Used for two chart types embedded in DOCX reports.

### make_traffic_line_chart

Line chart showing organic traffic trend over months.

```python
def make_traffic_line_chart(
    monthly_data: list[dict],
    width: float = 6.4,
    height: float = 4.6,
) -> bytes:
```

### make_psi_column_chart

Clustered column chart comparing Desktop vs Mobile PSI scores.

```python
def make_psi_column_chart(
    desktop_score: int | float,
    mobile_score: int | float,
    width: float = 4.6,
    height: float = 3.0,
) -> bytes:
```

### make_distribution_hbar_chart

Horizontal bar chart of keyword position distribution.

```python
def make_distribution_hbar_chart(
    distribution: dict,
    width: float = 5.0,
    height: float = 3.0,
) -> bytes:
```

### rank_trend_chart

Small line chart for a single keyword's rank trend over time.

```python
def rank_trend_chart(
    keyword: str,
    history_records: list[dict],
    width: float = 3.0,
    height: float = 1.5,
) -> bytes:
```

**Rules:**

- All functions return `bytes` containing PNG via `_save_fig(fig)` — never write to disk
- Charts use `matplotlib.use("Agg")` backend with custom `plt.rcParams.update()` for Calibri font, navy/gray palette, and minimal grid
- Always close the figure after saving: `plt.close(fig)`
- Chart resolution: 120 DPI (`DPI = 120`)

---

## Groq

Primary LLM provider for narrative generation.

### Project Pattern

```python
# modules/groq_client.py — always import from here
from modules.groq_client import GroqClient

client = GroqClient(api_key=GROQ_API_KEY, model=GROQ_MODEL)

result = client.chat(
    prompt=user_prompt,
    system_prompt="You are a senior SEO strategist...",
    max_tokens=4096,
    temperature=0.4,
)
```

Uses raw `requests` with `tenacity` retry (2 attempts, exponential backoff). Default model is `llama3-70b-8192` but overridden by `GROQ_MODEL` env var (typically `llama-3.3-70b-versatile`).

### Temperature Settings

- `0.4` — narrative generation (`llm_report_generator.py`)
- `0.3` — default in `GroqClient` class

### Max Tokens

- Full report narrative: `4096`
- Individual section generation (future): `1000`

### Anti-Hallucination Rules (Built into Prompt)

```
CRITICAL RULES:
1. Only use the data provided above. Do NOT invent any metrics, rankings,
   or strategies that are not present in the data.
2. If a section has no data (value is "—"), skip it entirely.
3. Never make up specific numbers, percentages, or rankings.
4. Apply general SEO knowledge to explain what the numbers mean, but never
   invent new numbers or data points.
5. Keep each section to 2-4 substantive paragraphs plus bullet points.
```

These rules are non-negotiable — the prompt builder in `llm_report_generator.py` always includes them.

---

## Tavily

Optional client auto-research when no pre-built profile exists.

### Project Pattern

```python
from tavily import TavilyClient

client = TavilyClient(api_key=TAVILY_API_KEY)

response = client.search(
    query=f"{client_name} luxury brand products pricing",
    search_depth="advanced",
    max_results=5,
)
```

**Rules:**

- Only used when client not in `CLIENT_PROFILES` dict
- Results cached in-memory during generation run
- Always use `search_depth="advanced"` for thorough results
- Never use Tavily for keyword position data — only for business context
- If Tavily returns no useful results, use a generic client placeholder rather than failing
