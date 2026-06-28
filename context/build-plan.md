# Build Plan

## Completed

### Phase 1 — Foundation
- Python project structure, dependencies, core data types
- `Evidence<T>` wrapper (value, source, timestamp, is_available)
- `ReportFacts` dataclasses (Kpidata, CWVData, RankingRow, TechnicalData, etc.)
- Evidence engine + facts loader + health score

### Phase 2 — DOCX Builders
- Client report: 15 cards (Cover → Summary & Next Steps)
- Action plan: 9 cards (Cover → Advisor Summary)
- Technical audit: 15 cards
- Charts (PSI column, rank distribution)
- DOCX verifier quality gate

### Phase 3 — LLM + Data
- Client context module (client_context.py)
- Client auto-research via Tavily (optional)
- LLM report generator (Groq Llama 3.3 70B)
- LLM action planner (OpenRouter GPT 120B with SEO skill prompt)
- Deterministic action plan fallback

### Phase 4 — Audit Pipeline
- Multi-tier crawl (Firecrawl → Playwright → BS4)
- PageSpeed Insights (API key + unauth)
- Multi-provider SERP (SerpApi → SearchApi → Apify)
- GSC + GA4 API integration
- Backlink analysis (Ahrefs cache + scrape)
- Playwright SERP preview (stealth + humanized)
- CAPTCHA detection + telemetry
- Thread-local Playwright (safe workers=4)
- File locking for shared resources

### Phase 5 — Backend API
- FastAPI server with 5 endpoints
- API key auth middleware
- Request validation
- DOCX download endpoint

### Phase 6 — Infrastructure
- Dockerfile with Playwright + OpenTelemetry
- Hugging Face Spaces deployment
- Grafana Cloud monitoring (auto-instrumentation)
- Upstash Redis (REST, 49 KB)
- Supabase Postgres (SSL cert)
- GitHub Actions CI
- Render Blueprint (alternate deploy)

## Not Yet Built

- `orchestrator/serp_snapshot.py` multi-provider pipeline not wired into audit workflow
- Supabase Postgres + Upstash Redis not actively used by API endpoints
- `audit_workflow.py` ~1300 lines needs refactoring
- Paid CAPTCHA solving integration (2captcha/Capsolver)
- Kubernetes / full production scaling