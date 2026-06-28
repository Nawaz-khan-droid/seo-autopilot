# SEO Autopilot — Project Overview

## What It Is

An automated SEO audit engine with a FastAPI backend, Docker-deployed on Hugging Face Spaces. Takes a client URL, crawls it with Playwright + APIs, collects metrics from 10+ sources, and outputs 3 DOCX files:

1. **Technical SEO Audit** — crawl + PSI + backlinks + link health
2. **Monthly SEO Report** — client-facing (rankings, GSC, CWV, off-page)
3. **SEO Action Plan** — LLM-generated (LLM fallback to deterministic generator)

## Architecture

```
main.py                   — CLI orchestrator (SERP → insights → reports)
api/main.py               — FastAPI server (REST endpoints, auth middleware)
api/audit_workflow.py     — ~1300-line core audit pipeline
├── Firecrawl → Playwright fallback → urllib/BS4 fallback
├── PSI (PageSpeed Insights)
├── SERP multi-provider (SerpApi → SearchApi → Apify)
├── GSC + GA4 APIs
├── Backlink analysis (Ahrefs cache + scrape)
├── Playwright SERP preview (stealth + humanized)
├── LLM action plan generation
└── DOCX builders (technical_audit, report, action_plan)
config/settings.py        — All env vars (Supabase, Upstash, GROQ, OTel)
modules/                  — 16 client modules (firecrawl, pagespeed, serp, etc.)
report/                   — DOCX builders, facts, evidence, charts, LLM narrative
orchestrator/             — serp_snapshot.py (multi-provider), site_audit, insights
```

## Data Sources (real data only — no synthetic)

| Source | Auth | Status |
|--------|------|--------|
| Firecrawl | API key | ✅ Primary crawler |
| Playwright headless | — | ✅ Fallback (thread-local, stealth) |
| SerpApi | API key | ✅ Rankings |
| SearchApi.io | API key | ✅ SERP fallback |
| Apify | API key | ✅ SERP enrichment |
| PageSpeed Insights | API key / unauth | ✅ CWV scores |
| Ahrefs cache | — | ✅ Backlinks (7-day TTL) |
| Google Search Console | service account | ✅ (requires GSC access) |
| Google Analytics 4 | service account | ✅ (requires GA4 access) |
| Google Sheets | service account | ✅ Keyword data source |
| Tavily | API key | ✅ Client research |
| Groq LLM | API key | ✅ Executive narratives |
| OpenRouter | API key | ✅ LLM fallback |
| Upstash Redis | REST URL + token | ✅ Serverless caching |
| Supabase Postgres | URL + SSL cert | ✅ Canonical DB (deploy-time) |

## Deployment

- **Platform**: Hugging Face Spaces (Docker SDK, CPU Basic)
- **URL**: https://jarvisllama-seo-autopilot.hf.space
- **Monitoring**: Grafana Cloud (OpenTelemetry auto-instrumentation)
- **Caching**: Upstash Redis (REST, 49 KB, no persistent TCP)
- **Database**: Supabase Postgres (IPv6-only, works from deploy platforms)
- **CI**: GitHub Actions (`.github/workflows/ci.yml`)

## Security

- Thread-local Playwright (no cross-request state)
- Isolated browser contexts per page (no cookie/storage leakage)
- API key auth middleware (X-API-Key header)
- Secrets via HF Space secrets (not in git)
- No synthetic/fake data — blank sections preferred
- `secrets/` in `.gitignore`
- `credentials.json` written at startup from `CREDENTIALS_JSON` secret

## Key Principles

- **Zero hallucinated data** — Every metric via `Evidence<T>` (value, source, confidence, timestamp)
- **Multi-tier fallback** — Every data source has 2-4 fallbacks before reporting `—`
- **CAPTCHA mitigation** — playwright-stealth + humanized behavior (mouse, scroll, delays)
- **DOCX quality gate** — `docx_verifier.py` scores output 0-100 post-generation