# SEO Autopilot — System Architecture & State

## Architecture Overview

```
Frontend (HTML/JS/CSS) ──HTTP──▶ FastAPI Backend ──▶ Google Sheets API
                                         │                ▼
                                         │         JSON Data Cache
                                         │         (output/data_cache/)
                                         │
                                         ├──▶ Firecrawl API (scrape public URLs)
                                         │
                                         └──▶ DOCX/PPT/PDF Generator
                                                   (report/)
                                                   (output/*.docx)
```

## Data Flow

### Client Reports (existing configured clients)
1. `main.py` Phases 1-5: collect SEO data (SERP, PageSpeed, BrowserOS, etc.) into Google Sheets
2. `main.py` Phase 6: read all sheet tabs → `facts_loader.build_facts()` → `build_clients_report()` + `build_action_plan_docx()`
3. API endpoint `POST /api/reports/generate`: loads from sheets (or cache) → generates same DOCX files
4. Data cache (`output/data_cache/`): per-tab JSON files created on each successful sheet read; used as fallback when sheets are unreachable

### Manual URL Audits (any public URL)
1. `POST /api/audit/run`: URL + crawl mode + optional sheet URL
2. `audit_workflow.py`: Firecrawl scrape/crawl → optional sheet read via `_try_open_sheet()` → `_build_facts_from_audit()` → chart mocks → `build_clients_report()` + `build_action_plan_docx()`
3. Returns file info (filename, size, download path)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server status + client count + data source info |
| GET | `/api/clients` | List configured clients (from sheets or cache) |
| POST | `/api/reports/generate` | Generate DOCX report for a client |
| POST | `/api/audit/run` | Run manual SEO audit on a URL |
| GET | `/api/reports/download/{filename}` | Download generated DOCX file |

## Clients (Beautiful India)
- 7 clients: Beauty & Fragrance, Personal Care, Home Care, Premium Collections,
  Bridal Collection, Luxury Gifts, Wellness & Relaxation
- All sub-brands of Beautiful India (global luxury lifestyle brand)

## Report Structure
- **Client Report** (15 cards): off-page (5), on-page (5), technical (5) → Executive tone → excludes raw CWV
- **Action Plan** (9 cards): Smart Advisor → Internal Team tone → includes LCP/INP/CLS

## Zero-Hallucination Contract
- Every metric is `Evidence<T>`: value + source + timestamp + confidence + proof_url
- Sections skip when data is empty (no filler text)
- Competition field normalised: Google decimal (0→low, 0.5→medium, 1.0→high)
- Charts Y-axis: `invert_yaxis()` + `set_ylim(min, max)` for rank trend

## Current State
- ✅ FastAPI backend (5 endpoints) — wired to frontend, no mock data
- ✅ FirecrawlClient — v4 SDK, scrape works, crawl falls back to scrape (API key limitation)
- ✅ Manual audit workflow end-to-end: URL → Firecrawl → ReportFacts → DOCX (verified: example.com generates 39 KB + 38 KB files)
- ✅ `.env` with FIRECRAWL_API_KEY + GROQ_API_KEY
- ✅ Data cache (JSON), rotating logs, lazy imports in generator.py
- ✅ Dual-mode frontend: Generator tab (existing clients) + Manual Audit tab (any URL)
- ✅ Two pre-existing blockers: test_browseros.py (TypeError), issues #8/#9 (ai_analysis/serp_snapshot)
