# SEO Autopilot — Agent Handoff

## Project Overview

Automated SEO audit + monthly report generator. Takes a client URL, crawls it
with multiple engines, collects metrics, and outputs 3 DOCX files:
- Technical SEO Audit
- Monthly SEO Report (client-facing)
- SEO Action Plan (internal team)

## Architecture

```
main.py               — CLI orchestrator (SERP pipeline, insights, reports)
api/
  main.py             — FastAPI server (endpoints for web UI, ~749 lines)
  audit_workflow.py   — core audit orchestrator + quick scan (~386 lines)
  crawl_engine.py     — tiered crawl: Playwright → cloud → pyseoanalyzer → urllib (~780 lines)
  parallel_fetch.py   — PSI, backlinks, GSC, GA4, SERP, Trends, CWV (~634 lines)
  facts_assembler.py  — ReportFacts builder from crawl + API data (~276 lines)
  browser_manager.py  — Playwright TLS lifecycle (~193 lines)
  rate_limiter.py     — Redis-backed + in-memory fallback (~170 lines)
  error_resolver.py   — structured error classification and recovery
  data_cache.py       — JSON-based report cache with TTL expiry
modules/
  seo_rules/          — 269 CrawlForge-derived SEO rules (DuckDB in-memory)
  firecrawl_client.py — FirecrawlApp SDK wrapper (primary crawl engine)
  serp_client.py      — SerpApi rank tracking
  searchapi_client.py — SearchApi.io rank tracking
  apify_client.py     — Apify Google Search Scraper
  browseros_client.py — BrowserOS CDP client (Playwright-based)
  pagespeed_client.py — PageSpeed Insights API
  backlink_client.py  — DuckDuckGo + OpenPageRank backlink finder
  search_console.py   — Google Search Console API
  ga4_client.py       — Google Analytics 4 Data API
  sheet_client.py     — Google Sheets read/write
  tavily_client.py    — Tavily AI search (client discovery)
  groq_client.py      — Groq LLM client
  openrouter_client.py— OpenRouter LLM fallback
  niche_classifier.py — Multi-signal business niche detection
  client_memory.py    — Tavily-based client profile cache
  url_utils.py        — Canonical URL matching, SSRF guard
  http_pool.py        — Shared HTTPX connection pool (sync + async)
  logger_config.py    — Logging setup
  pagespeed.py        — PSI auth strategy (API key → OAuth → unauthenticated)
report/
  facts.py            — Dataclasses: Evidence, ReportFacts, TechnicalData, etc.
  docx_technical_audit.py  — Technical audit DOCX builder
  docx_report.py           — Monthly report DOCX builder
  docx_action_plan.py      — Action plan DOCX builder
  docx_verifier.py         — Post-generation DOCX quality gate
  charts.py           — Matplotlib charts (PSI column, rank distribution)
  llm_narrative.py    — LLM-generated executive summaries
  evidence.py         — Evidence with provenance (missing/estimated/verified)
orchestrator/
  serp_snapshot.py    — Multi-provider rank detection workflow
  site_audit.py       — Site crawl + audit sheet writer
  website_insights.py — BrowserOS performance + PSI + GSC insights
config/
  settings.py         — Environment variable loader (.env)
  serp_config.py      — Provider hierarchy and feature flags
output/              — Generated DOCX files land here
```

## Data Flow (Audit)

```
0. _quick_page_scan(url) — HTTP + BS4, <5s, guaranteed (runs first in demo)

1. _run_audit_impl(url, sheet_url, mode)
   │
   ├─ FirecrawlClient.scrape_page(url)        # Tier 1: Firecrawl
   │   └─ fallback: api.crawl_engine.run_local_opensource_seo_audit(url)
   │       ├─ Playwright headless (domcontentloaded)  # Tier 2a
   │       ├─ Cloud stealth browser           # Tier 2b
   │       ├─ pyseoanalyzer                   # Tier 3
   │       └─ urllib/BeautifulSoup            # Tier 4
   │
   ├─ api.parallel_fetch: _fetch_parallel(url)
   │   ├─ fetch_pagespeed_metrics(mobile/desktop)  # PSI scores
   │   ├─ fetch_backlinks                          # DuckDuckGo + OPR
   │   ├─ _fetch_gsc_data                          # GSC API
   │   └─ _fetch_ga4_data                          # GA4 API
   ├─ api.crawl_engine: _check_link_health(hrefs)   # HTTP HEAD per link
   ├─ api.parallel_fetch: _fetch_rankings_via_serp  # API cascade → Playwright → title fallback
   ├─ api.parallel_fetch: _fetch_google_trends      # SerpApi Trends
   ├─ api.parallel_fetch: _capture_serp_preview     # Playwright SERP screenshot
   │
   ├─ modules.seo_rules: run_seo_rules(url, local_metrics)  # 269 DuckDB rules
   │
   ├─ api.facts_assembler: _build_facts_from_audit  # Assemble ReportFacts
   ├─ api.facts_assembler: _ensure_facts_data       # Fill gaps with estimates
   │
   ├─ build_technical_audit(facts, path, serp_preview)  # DOCX #1
   ├─ build_clients_report(facts, path, trends_data)    # DOCX #2
   └─ build_action_plan_docx(facts, path)               # DOCX #3
```

## Key Decisions (recent)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06 | **No synthetic rankings** — removed all sample keyword rows from `_ensure_facts_data` and `_build_facts_from_audit` | User detected fake data in reports. Rankings now come from sheets or live SERP check only |
| 2026-06 | **GSC/GA4 APIs integrated** — `_fetch_gsc_data` and `_fetch_ga4_data` called before `_build_facts_from_audit` | Modules existed but were never invoked. KPI data was always `—` |
| 2026-06 | **Access Required badge — GSC only** — other sections show `—` when no data | Rankings have alternatives (sheets, SERP tools) so no badge needed there |
| 2026-06 | **Data priority chain**: GSC API → sheet traffic tab → `—` | First try the authoritative API, then user-uploaded data |
| 2026-06 | **SERP rank tracking** — auto-discovers keywords from page content, checks via SerpApi | User has open source SEO tools and wanted them used |
| 2026-06 | **Google Trends card** in Monthly Report | Uses SerpApi `engine=google_trends`. New card between GSC Performance and Brand Keyword Rankings |
| 2026-06 | **Playwright SERP preview** — `_capture_serp_preview` screenshots Google search result for `site:domain` | User wanted search preview image in the audit |
| 2026-06 | **DOCX verifier** — `docx_verifier.py` runs after generation, scores quality 0-100 | Catches empty sections before delivery |
| 2026-06 | **`has_schema` field** on `TechnicalData`, mapped from crawler payload | Schema detection existed but wasn't surfaced in reports |
| 2026-06 | **LLM-driven action plan** — `report/llm_action_planner.py` + `report/seo_action_planner_skill.md` | Removed all hardcoded action items from `audit_workflow.py`. Action plan now generated via OpenRouter GPT 120B with an SEO expertise skill prompt. Falls back to deterministic `action_plan_generator.py` if LLM is unavailable |
| 2026-06 | **Playwright security hardening** — `_get_browser_page()` creates fresh isolated context per page via `_secure_context()`. No cookie/storage/SW leakage between sites. Browser launched with security args. All permission prompts blocked. | Visited client sites could serve exploit code. Site isolation prevents cross-site state leakage and removes dangerous browser surface area. |
| 2026-06 | **playwright-stealth applied to all pages** — `_STEALTH_HOOK.apply_stealth_sync(page)` called in `_run_playwright_headless`, `_capture_page_preview`, and `_capture_serp_preview` before navigation. SERP preview also uses humanized mouse/scroll/delay simulation. | Reduces CAPTCHA blocking on Google SERP queries. Module was installed but never invoked. |
| 2026-06 | **Tracker blocking rejected for `_secure_context`** — considered route-level blocking of ad/tracker/malware domains but rejected | For an SEO audit tool that analyzes on-site analytics/trackers, blocking them would distort the page data. Site isolation provides sufficient security. |
| 2026-06 | **Thread-local Playwright browser** — `_PLAYWRIGHT_TLS` (threading.local) replaces global `_PLAYWRIGHT_INSTANCE` / `_BROWSER_INSTANCE` singletons | Enables safe `workers=4` with uvicorn. Each request thread owns its own Playwright instance — no cross-thread state conflicts. Browser auto-launched on first `_get_browser_page()` call per thread, destroyed by `_close_browser()` at request end. |
| 2026-06 | **File locking for shared resources** — `filelock` (FileLock) wraps `captcha_telemetry.json` and rank cache writes | Prevents corruption when multiple worker processes write to the same file simultaneously. |
| 2026-06 | **API authentication** — new `APIKeyMiddleware` checks `X-API-Key` header on all `/api/` routes (except health + OPTIONS) | Configurable via `API_AUTH_KEY` env var — empty = disabled (local dev). |
| 2026-06 | **CSV upload validation** — `_validate_backlink_csv()` checks header normalisation, encoding, and required columns (`total_backlinks` + `ref_domains` at minimum) | Prevents malformed or incorrect CSV files from being stored. |
| 2026-06 | **uvicorn workers=4** — changed from `reload=True, workers=1` to `workers=4, reload=False` with `WEB_CONCURRENCY` env override | Enables concurrent request handling via forked processes. Each worker has independent thread-local state. |
| 2026-07 | **CrawlForge rules integrated** — 269 rules cloned into `modules/seo_rules/`, DuckDB in-memory per audit | Issues feed into `TechnicalData.issues_list`, health score penalised by severity. Cap of 30 penalty points, rules issues count toward total `issues` count |
| 2026-07 | **Quick scan guaranteed** — `_quick_page_scan()` via HTTP+BS4 runs before full audit in demo mode, stores immediately, persists on failure | Removes "all or nothing" failure mode. Sometimes returns "Missing H1/Meta/Alt" as quick issues |
| 2026-07 | **Playwright crawl: `domcontentloaded`** replaces `networkidle` for CWV pages and crawl | 3-5s vs 30s+. SERP fallback unchanged. CWV Playwright timeout reduced from 45s→10s |
| 2026-07 | **Redis rate limiter: sync `redis-py`** replaces broken `redis.asyncio` in sync context | `redis.asyncio` never awaited — rate limiter silently always returned `True`. Now uses sync client with `ping()` validation |
| 2026-07 | **close_all_browsers race fixed** — iterates thread IDs under lock, clears set atomically | Previously modified set outside lock (race), only closed caller's TLS instead of tracking all threads |
| 2026-07 | **Health score double-counting eliminated** — rules penalties applied once, not twice | Old code subtracted rules penalty THEN `len(issues_list)*5`. Now single capped penalty from issues + rules |
| 2026-07 | **Job dict capped at 500 entries** — cleanup evicts oldest first when over limit | Prevents memory leak under heavy load |
| 2026-07 | **DuckDB connection None-guard** — `init_database()` failure doesn't crash `finally: con.close()` | `con` initialised to `None`, only closed if not None |
| 2026-07 | **Dead code removed** — `streamlit_app.py` deleted, Dockerfile/requirements.txt updated, git history cleaned of `secrets/supabase-ca.crt` + test DOCX files | filter-branch rewrote history (31→27 commits) |
| 2026-07 | **Issues in API response** — `_generate_deliverables()` now includes `issues` array with `{page, issue_text, severity}` | Demo quick scan also generates basic issues for missing H1/Meta/Alt |

## Data Provenance

Every metric in the reports carries an `Evidence` object with:
- `value` — the actual data
- `source` — where it came from (e.g. `"SerpApi"`, `"PSI mobile"`, `"Synthetic Baseline"`)
- `confidence` — `verified`, `estimated`, or `missing`
- `timestamp` — when it was collected

Use `_ev()` in DOCX builders to display (shows `—` if missing/None).
Use `_evi()` to get an integer value (returns 0 if missing).

## Known Issues

1. **GSC auth** — the service account email (`credentials.json`) must be added to each GSC property manually. Until then, GSC shows "Access Required"
2. **PSI rate limiting** — PageSpeed Insights returns `rate_limited` after ~10 queries/min without an API key. The module doesn't retry
3. **Playwright CAPTCHA** — Google sometimes blocks headless browser SERP queries with a CAPTCHA page. Mitigated by playwright-stealth + humanized behavior (mouse, scroll, delays). CAPTCHA telemetry at `output/captcha_telemetry.json` tracks success rate. Consider paid CAPTCHA solving (2captcha/Capsolver) if success rate drops below 50%
4. **Backlink cache staleness** — `backlink_client.py` uses a 7-day TTL JSON cache. Data may be outdated for weekly reports
5. **Action plan only generates 2 tasks** — hardcoded generic tasks. Sheet-driven or LLM-generated plans are not implemented *(FIXED: now LLM-driven via GPT 120B SEO skill)*
6. **The `import re` bug** — there was a local `import re` inside a loop in `audit_workflow.py` line 962 that shadowed the global import and caused `UnboundLocalError`. Already fixed — DO NOT reintroduce nested imports inside functions that also use the same module at the top level
7. **Health score double-counting FIXED** (was: rules penalty + `len(issues)*5` applied twice)
8. **Redis rate limiter FIXED** (was: `redis.asyncio` used in sync method, never awaited)
9. **`git filter-branch` wiped working changes on 2026-07-01** — commit before running history rewrite. Uncommitted changes are lost
10. **`streamlit_app.py` deleted** — was unused dead code. `streamlit` removed from `requirements.txt`, Dockerfile updated
11. **Secrets in git history: NONE FOUND** (in this repo). Previous AGENTS.md claim was incorrect. `secrets/supabase-ca.crt` (public cert) and `scripts/_test_output/*.docx` purged from history
12. **No additional cryptography needed** (PS-09) — SHA-256 for idempotency, `hmac.compare_digest` for API key, default TLS verification in httpx. Gap: TLS termination at reverse proxy layer (not app code)
13. **CWV Playwright uses `domcontentloaded`** (not `networkidle`) — 10s timeout vs 45s. May miss late-loading resources
14. **269 SEO rules: 92 issues typical on real sites** — 0 critical, ~30 warning, ~62 info. Health score penalised max 30 points from rules

## Common Runtime Errors & Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| HTTP 500 "UnboundLocalError" | Nested `import re` inside a loop | Remove local import, use the global one |
| GSC shows "Access Required" | Service account not added to GSC property | Add `credentials.json` email to GSC → Settings → Users |
| All KPIs show `—` | GSC not configured AND no sheet with traffic tab | Set `GSC_SITE_URL` in .env OR provide a sheet with a "Traffic"/"Clicks" tab |
| Rankings show `—` | No sheet with keyword tab AND no `SERPAPI_KEY` | Set `SERPAPI_KEY` in .env OR provide a sheet with a "Keywords" tab |
| "Playwright not available" | `playwright` not installed | `pip install playwright && playwright install chromium` |
| DOCX quality score < 50 | Most paragraphs are empty → crawl failed to collect data | Check the log for the specific tier failure (Playwright, PSI, etc.) |
| Audit timeout (>120s) | Slow page, PSI rate limit, or Firecrawl crawl | Use single-page mode, check PSI quota |

## Configuration (.env)

```
GROQ_API_KEY=required
SERPAPI_KEY=optional          # SERP rank tracking + Google Trends
PAGESPEED_API_KEY=optional    # Increases PSI rate limit
CREDENTIALS_PATH=credentials.json  # Google service account JSON
GSC_SITE_URL=sc-domain:example.com  # Or full https:// URL
GA4_PROPERTY_ID=123456789     # Numeric GA4 property ID
APIFY_API_KEY=optional        # SERP enrichment
SEARCHAPI_API_KEY=optional    # SERP fallback
BROWSERLESS_API_KEY=optional  # Cloud browser fallback
PROVIDER_ORDER=serpapi,apify,browseros,searchapi  # Override SERP provider order
```

## File Size Reference

- `crawl_engine.py` — 527 lines (tiered crawl orchestrator)
- `parallel_fetch.py` — 525 lines (PSI, backlinks, GSC, GA4, SERP, Trends)
- `audit_workflow.py` — 379 lines (core audit orchestrator, was 1967)
- `facts_assembler.py` — 267 lines (ReportFacts builder)
- `browser_manager.py` — 167 lines (Playwright TLS lifecycle)
- `docx_report.py` — ~1100 lines (largest DOCX builder)
- `serp_snapshot.py` — ~860 lines (complex orchestrator)
- `browseros_client.py` — ~560 lines (most complex module)
- `facts.py` — ~280 lines (all dataclasses)

## Handoff Guidance

For the next agent working on this codebase:

1. **Start with `docx_verifier.py`** — run it on existing reports to identify quality gaps. Fix the lowest-scoring sections first
2. **The DOCX builders** (`docx_report.py`, `docx_technical_audit.py`) are the highest-value files to improve — they directly affect what the user sees
3. **If adding a new data source**, add it to the priority chain in `_build_facts_from_audit()`. Always use `Evidence.verified()` for real data, `Evidence.estimated()` for fallbacks
4. **Never generate synthetic/fake data** — the user explicitly rejected this. Use `—` or skip the section instead
5. **The `error_resolver.py`** module is new — migrate existing try/except blocks to use `resolve_error()` for consistent logging and recovery
6. **Test changes by running** `run_audit(url='https://example.com')` — this exercises the full pipeline without needing a real client site
7. **Avoid nested imports** inside functions that shadow top-level imports (causes `UnboundLocalError`)
8. **The SERP rank tracking** has a full multi-provider pipeline in `orchestrator/serp_snapshot.py` that is NOT integrated into the audit workflow — it could be wired in for richer keyword data
9. **`_secure_context(browser)` in `api/browser_manager.py`** creates a new isolated Playwright context per page call. If adding a new Playwright page user, always go through `_get_browser_page()` (not `browser.new_page()` directly) to get security hardening
10. **CAPTCHA telemetry** at `output/captcha_telemetry.json` — if the success rate drops below 50%, consider integrating a paid CAPTCHA solving service (2captcha, Capsolver) in `_capture_serp_preview()` before the CAPTCHA detection check
11. **Phase 2 extraction pattern** — `audit_workflow.py` was 1967 lines, now ~386. Extracted modules import back into `audit_workflow.py`. To add more extractions, create new `api/*.py` modules and import them — never inline new code into `audit_workflow.py` directly.
12. **Rules engine** (`modules/seo_rules/_runner.py:run_seo_rules()`) runs after `run_local_opensource_seo_audit()` in `_run_audit_impl()`. Takes crawl_data dict, returns list of issue dicts. Populates DuckDB in-memory, runs all 269 rules, exports issues. Call already wired: `audit_workflow.py:368`
13. **`_build_facts_from_audit()`** accepts `seo_rules_issues` kwarg (list of dicts). Issues merged into `facts.technical.issues_list`. Health score penalised by severity: `critical/warning`=3pts, `info`=1pt, capped at 30pts total. Does NOT double-count issues (was fixed 2026-07-01)
14. **`_quick_page_scan()`** in `audit_workflow.py` is the guaranteed <5s HTTP+BS4 scan. Used by demo mode (`main.py:_run_demo_background()`) as immediate result before full audit enriches. Never throws — always returns at least default metrics with `health_score=85`
15. **API response `issues` array** — `_generate_deliverables()` appends `issues: [{page, issue_text, severity}]` from `facts.technical.issues_list`. Quick scan also generates basic issues for missing H1/Meta/Alt
16. **Rate limiter** uses sync `redis-py` (not `redis.asyncio`). Falls back to in-memory. `_check_redis()` uses `zremrangebyscore → zcard → zadd → expire` pattern
17. **Use `python -m pytest tests/ -x -q -k "not perf and not guardrail"`** to run tests. The `-k "not perf"` skips tests needing localhost:8000. Guardrail tests need specific PPT internals
18. **`git filter-branch` hazard** — always commit before rewriting history. Uncommitted changes are permanently lost
