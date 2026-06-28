# Code Standards

Implementation rules and conventions for the entire project. The AI agent must follow these in every session without exception.

---

## Engineering Mindset

The AI agent on this project operates as a senior engineer. This means:

- **Think before implementing** — understand what is being built and why before writing a single line
- **Read context files first** — never assume, always verify against architecture.md and project-overview.md
- **Scope is sacred** — only build what the current feature requires. Never go beyond scope even if it seems helpful
- **Every feature must be verifiable** — if it cannot produce a DOCX file that opens and renders correctly, it is incomplete
- **Clean over clever** — simple readable code that a junior developer can understand is always preferred over clever abstractions
- **One thing at a time** — complete one feature fully before touching the next
- **Data integrity first** — every metric must be wrapped in `Evidence<T>`. Never inject unverified data.
- **Empty sections are hidden** — if a data field is empty, the corresponding section must not render at all. No "no data" placeholders.

---

## Python

- Type hints required on all function parameters and return types — no exceptions
- Never use `Any` unless absolutely necessary and justified in a comment
- Use `from __future__ import annotations` at the top of every module for forward references
- Use dataclasses for data containers — never raw dicts for structured data
- All Evidence values are accessed through `_ev()` helper — never access `.value` directly
- Use `is_available` to check `Evidence` before rendering — never assume data exists
- Snake_case for functions, variables, file names
- PascalCase for classes and dataclasses
- UPPER_CASE for constants
- `_prefix` for private / helper functions
- All async functions must have proper error handling — never let exceptions crash the report

---

## DOCX Builder Conventions

Every DOCX builder follows this exact pattern:

```python
from __future__ import annotations

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

from report.facts import ReportFacts

# ── Palette ──
NAVY = RGBColor(0x0F, 0x27, 0x47)
ACCENT = RGBColor(0x25, 0x63, 0xEB)
# ... etc

FN = "Calibri"

# ── Helper functions ──
def _shd(cell, c): ...
def _cell(cell, text, bold=False, color=None, size=10, align=None): ...
def _para(doc, text, bold=False, color=None, size=10, align=None, before=0, after=0): ...
def _bullets(doc, items, size=10): ...
def _ev(v): ...

# ── Main builder ──
def build_name_here(facts: ReportFacts) -> bytes:
    doc = Document()
    # ... build sections
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
```

- Every builder returns `bytes` — never write to disk directly inside the builder
- Callers handle file writing with timestamped filenames
- Always use `io.BytesIO` for buffered output
- Never use inline styles — use the helper functions
- Default font size is 10pt (body) and 18pt (section titles)

---

## Evidence Usage

```python
from report.evidence import Evidence

# Creating
ev = Evidence.verified("430", "GSC")  # value, source
ev = Evidence.missing()  # placeholder when data unavailable

# Reading (always through _ev helper)
val = _ev(some_evidence)  # returns str or "—"
if some_evidence.is_available:
    process(some_evidence.value)
```

- Never call `.value` directly — always use `_ev()` helper
- Always check `is_available` before rendering data in DOCX
- Never mutate an Evidence object after creation

---

## Error Handling

- Never use empty except blocks — always log or handle
- Log errors with context prefix: `[module/function]`
- Report generation should never crash on missing data — skip the section instead
- API calls (Groq, Tavily) wrapped in try/except — fall back gracefully
- Console logging via `logging.getLogger(__name__)` — never print()

---

## Environment Variables

All environment variables defined in `.env`. Never hardcode any key, URL, or secret anywhere in the codebase.

| Variable                | Required | Used In                         |
| ----------------------- | -------- | ------------------------------- |
| `GROQ_API_KEY`          | Yes      | modules/groq_client.py          |
| `SERPAPI_KEY`           | Yes*     | SERP data provider (marked required in .env.example) |
| `GROQ_MODEL`            | No       | Default: `llama3-70b-8192` in client, overridden to `llama-3.3-70b-versatile` via settings.py |
| `TAVILY_API_KEY`        | No       | report/client_research.py       |
| `OPENROUTER_API_KEY`    | No       | Fallback LLM provider           |
| `PAGESPEED_API_KEY`     | No       | Live CWV data collection        |
| `SEARCHAPI_API_KEY`     | No       | Alternative SERP provider       |
| `APIFY_API_KEY`         | No       | SERP enrichment                 |
| `GSC_SITE_URL`          | No       | Google Search Console           |
| `GA4_PROPERTY_ID`       | No       | Google Analytics 4              |
| `CREDENTIALS_PATH`      | No       | Google API credentials          |
| `SHEET_NAME`            | No       | Google Sheet name               |
| `MAX_KEYWORDS`          | No       | Runtime keyword limit (default 999, clamped 1-9999) |
| `PROVIDER_ORDER`        | No       | SERP provider priority order    |

---

## Imports

Standard library imports first, then third-party, then local. Groups separated by blank lines.

```python
import os
import logging
from datetime import datetime
from typing import Any

from docx import Document
from docx.shared import Inches, Pt, RGBColor

from report.facts import ReportFacts
from report.evidence import Evidence
```

---

## Comments

- No comments explaining what the code does — code must be self-explanatory
- Comments only for why — explaining a non-obvious decision
- Module-level docstring always present explaining the module's purpose
- Never leave TODO comments in committed code

---

## Dependencies

Never install a new package without a clear reason. Before installing anything check:

1. Can Python's standard library do this?
2. Is there an existing package in `requirements.txt` that already does this?
3. Is the package well-maintained and compatible with Python 3.11+?

Approved dependencies for this project:

- `python-docx` — DOCX report builder
- `matplotlib` — Charts (distribution, PSI comparison)
- `requests` — HTTP client (used in GroqClient, SERP providers)
- `tenacity` — Retry logic for API calls (GroqClient)
- `tavily-python` — Client auto-research
- `python-dotenv` — Env var loading
- `python-pptx` — PPT generation (reference only, not primary)
- `reportlab` — PDF report builder (reference only, `renderer.py`)
- `PyMuPDF` — PDF text extraction (reference only)
- `pdfminer.six` — PDF parsing (reference only)
- `playwright` — Screenshot capture (`screenshots.py`)
- `groq` — LLM API (optional, direct SDK; only if replacing `requests`‑based client)

Do not install any other packages without updating this list first.
