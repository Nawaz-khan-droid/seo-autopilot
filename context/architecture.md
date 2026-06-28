# Architecture

## High Level

```
User Request
    │
    ▼
FastAPI (api/main.py)
    │
    ├── Auth Middleware (X-API-Key check)
    │
    ├── /api/health → status + groq_configured
    ├── /api/clients → list from client_context.py
    └── /api/reports/generate
            │
            ▼
        audit_workflow.py (run_audit)
            │
            ├── FirecrawlClient.scrape_page(url)
            │   └── fallback: Playwright headless (thread-local, stealth)
            │       └── fallback: pyseoanalyzer / urllib+BS4
            │
            ├── fetch_pagespeed_metrics(url, mobile)  ← PSI API
            ├── fetch_backlinks(url)                   ← Ahrefs cache + scrape
            ├── _check_link_health(hrefs, url)         ← HTTP HEAD per link
            ├── _fetch_gsc_data(url)                   ← GSC API
            ├── _fetch_ga4_data()                      ← GA4 API
            ├── _fetch_rankings_via_serp(url)           ← multi-provider
            ├── _fetch_google_trends(keyword)           ← SerpApi Trends
            ├── _capture_serp_preview(url)              ← Playwright + stealth
            │
            ├── _build_facts_from_audit() → ReportFacts
            ├── _ensure_facts_data(facts) ← gap estimates
            │
            ├── build_technical_audit(facts) → DOCX #1
            ├── build_clients_report(facts) → DOCX #2
            └── build_action_plan_docx(facts) → DOCX #3
```

## Data Flow

```
Data Sources (API calls)
    │
    ▼
Evidence<T> (value + source + confidence + timestamp)
    │
    ▼
ReportFacts (unified data container)
    │
    ├── docx_verifier.py (quality gate, score 0-100)
    │
    ├── docx_technical_audit.py    → Technical SEO Audit.docx
    ├── docx_report.py             → Monthly SEO Report.docx
    └── docx_action_plan.py        → SEO Action Plan.docx
```

## Module Directory

```
api/              FastAPI server + audit pipeline
modules/          16 client modules (firecrawl, pagespeed, serp, gsc, ga4, etc.)
report/           DOCX builders + facts + evidence + charts + LLM narrative
orchestrator/     serp_snapshot, site_audit, website_insights
config/           settings + serp_config + prompts
monitoring/       Prometheus + Grafana config
tests/            166 tests (3 E2E)
secrets/         .gitignore'd (credentials.json, supabase-ca.crt)
```

## Deployment Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (uvicorn, workers=4) |
| Container | Docker (python:3.13-slim + Playwright) |
| Host | Hugging Face Spaces (CPU Basic, 2 vCPU 16GB) |
| Monitoring | Grafana Cloud (OpenTelemetry auto-instrumentation) |
| Caching | Upstash Redis (REST API, 49 KB) |
| Database | Supabase Postgres (IPv6-only, SSL) |
| CI | GitHub Actions |
| Alternate | Render (render.yaml Blueprint) |

## Key Design Decisions

1. **Thread-local Playwright** — Each uvicorn worker owns its own browser instance, no cross-thread state
2. **Multi-tier fallback** — Every data source has 2-4 fallbacks before reporting `—`
3. **No synthetic data** — Blank sections over invented metrics
4. **Evidence<T> wrapper** — Every metric tracks source + confidence + timestamp
5. **REST-based Redis** — Upstash REST client (49 KB, no persistent TCP, no port management)
6. **LLM + deterministic fallback** — Action plan tries LLM first (OpenRouter GPT 120B), falls back to deterministic generator