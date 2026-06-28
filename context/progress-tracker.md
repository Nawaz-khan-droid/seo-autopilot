# Progress Tracker

## Current Status

**Phase:** Deployed — HF Spaces live, Grafana OTel monitoring active
**Last completed:** DOCX bugs fixed (c/p2 undefined variables)
**Next:** Wire Supabase + Upstash into FastAPI startup

---

## Completed

### Core Pipeline
- [x] FastAPI server with 5 endpoints (/health, /clients, /reports/generate, etc.)
- [x] API key authentication middleware
- [x] Multi-tier crawl engine (Firecrawl → Playwright → BS4)
- [x] PageSpeed Insights (API key + unauthenticated fallback)
- [x] Multi-provider SERP rank tracking (SerpApi → SearchApi → Apify)
- [x] GSC + GA4 API integration
- [x] Backlink analysis (Ahrefs cache + scrape)
- [x] Playwright SERP preview with stealth + humanized behavior
- [x] CAPTCHA telemetry tracking
- [x] Thread-local Playwright for safe concurrent workers
- [x] DOCX verifier quality gate
- [x] LLM-based action plan generation via OpenRouter GPT 120B
- [x] Deterministic action plan fallback
- [x] DOCX builders: technical audit (15 cards), report (15 cards), action plan (9 cards)
- [x] Matplotlib charts (PSI column, rank distribution)

### Infrastructure
- [x] Dockerfile with Playwright deps
- [x] HF Spaces deploy (Docker SDK, CPU Basic)
- [x] OpenTelemetry auto-instrumentation for Grafana Cloud
- [x] Upstash Redis (REST, 49 KB client)
- [x] Supabase Postgres configuration (SSL cert)
- [x] GitHub repo + Actions CI
- [x] Render Blueprint (render.yaml, alternate deploy target)

### Security
- [x] Isolated Playwright contexts (no cross-site state)
- [x] playwright-stealth on all pages
- [x] Secrets in `.gitignore` + HF Space secrets
- [x] API key middleware
- [x] File locking for shared resources (captcha telemetry, rank cache)

### Code Quality
- [x] 166 passing tests, 3 E2E
- [x] AGENTS.md handoff document
- [x] Context docs updated to current project state

---

## Known Issues

| Issue | Status |
|-------|--------|
| GSC shows "Access Required" | Need to add service account email to GSC property |
| PSI rate limiting (~10/min without key) | No retry implemented |
| Playwright CAPTCHA on Google SERP | Mitigated (stealth + humanized), telemetry at `output/captcha_telemetry.json` |
| Backlink cache 7-day TTL | Data may be stale for weekly reports |
| `audit_workflow.py` ~1300 lines | Refactoring deferred post-deploy |
| 24 pre-existing test failures (browseros) | Not updated after refactor |

---

## Next Steps

1. Wire Supabase Postgres + Upstash Redis into FastAPI startup (currently configured but not active)
2. Add GSC service account to GSC property
3. Refactor `audit_workflow.py` into smaller modules
4. Integrate `orchestrator/serp_snapshot.py` multi-provider pipeline into audit workflow
5. Consider paid CAPTCHA solving if success rate drops below 50%