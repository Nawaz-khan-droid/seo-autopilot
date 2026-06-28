# SEO Autopilot

Automated SEO audit pipeline + multi-client report generator. Crawls any URL, collects 50+ SEO metrics, and produces 3 DOCX deliverables.

## Quick Start

```bash
pip install -r requirements.txt
playwright install chromium
```

Copy `.env.example` to `.env` and set at minimum:

```env
GROQ_API_KEY=your_groq_key_here
```

Run an audit on any URL:

```bash
python -m api.main
curl -X POST http://localhost:8000/api/audit/run \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Pipeline

```
User URL
  │
  ├─ Firecrawl API              (Tier 1 — primary)
  │   └─ Playwright headless    (Tier 2a — fallback)
  │       └─ Cloud stealth      (Tier 2b — via browserless.io)
  │           └─ pyseoanalyzer  (Tier 3 — optional)
  │               └─ urllib/BS4 (Tier 4 — last resort)
  │
  ├─ PageSpeed Insights         (mobile + desktop)
  ├─ Google Search Console      (clicks / impressions)
  ├─ Google Analytics 4         (users / sessions)
  ├─ SerpApi rank tracking      (keyword positions)
  ├─ Google Trends              (interest over time)
  ├─ Link health check          (HTTP HEAD per href)
  └─ SERP preview screenshot    (Playwright)
       │
       └─ ReportFacts → 3 DOCX files
            ├─ Technical Audit
            ├─ Monthly Report (client-facing)
            └─ Action Plan (internal)
```

## Security

All endpoints hardened against OWASP Top 10:

| Protection | Mechanism |
|---|---|
| SSRF (API layer) | Private IP block covering all RFC 1918 ranges + cloud metadata hosts (169.254.x, fd00::/8) |
| SSRF (DNS layer) | `_resolve_and_validate_target()` — resolves hostname to IP and rejects private addresses before any outbound request |
| Path traversal | `resolve()` + `.startswith()` guard on all file-serving endpoints; `client_name` sanitized for `..`, `/`, `\`, `:` |
| Timing attack | API key comparison uses `hmac.compare_digest()` |
| Rate limiting | Sliding-window limiter (10 req/min/IP) on audit endpoints |
| Dependency CVEs | `urllib3>=2.7.0` (6 CVEs fixed), `python-dotenv>=1.2.2` (CVE-2026-28684) |
| Secrets | `.gitignore` covers `.env`, `credentials.json`, `secrets/credentials.json`, `*.pem`, `*.key` |
| TLS | Optional via `SSL_CERTFILE`/`SSL_KEYFILE` env vars; `scripts/setup_ssl.py` generates self-signed certs |

258 passing tests (49 security-specific), 0 failures.

## Architecture

```
api/
  main.py              — FastAPI server (audit, generate, download, upload)
  audit_workflow.py    — Audit orchestrator (379 lines)
  crawl_engine.py      — Tiered crawl + link health + CAPTCHA telemetry (527 lines)
  parallel_fetch.py    — PSI, backlinks, GSC, GA4, SERP, Trends, CWV, previews (525 lines)
  facts_assembler.py   — ReportFacts builder from crawl + API data (267 lines)
  browser_manager.py   — Playwright TLS lifecycle (167 lines)
  error_resolver.py    — Structured error classification
  data_cache.py        — JSON report cache with TTL

modules/              — Individual API clients (SerpApi, Groq, GSC, GA4, etc.)
report/               — DOCX builders, charts, evidence model, LLM narratives
orchestrator/         — SERP snapshot, site audit, website insights, monthly plan
config/               — Settings, provider hierarchy, location maps
tests/                — 258 tests (pytest)
```

## Key Design Decisions

- **Zero fake data** — every metric carries `Evidence<T>` with source, confidence, timestamp. Missing data shows `—`, never invented
- **LLM-enhanced, not LLM-dependent** — each AI component has a deterministic fallback (rule-based analysis, template reports)
- **Multi-provider SERP** — SerpApi → Apify → BrowserOS → SearchApi.io chain with per-provider circuit breaker
- **Security first** — two-layer SSRF defense (API host check + DNS-level IP validation), timing-safe auth, path traversal protection

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | LLM for narratives and analysis |
| `SERPAPI_KEY` | No | — | Rank tracking + Google Trends |
| `PAGESPEED_API_KEY` | No | — | PSI rate limit increase |
| `CREDENTIALS_PATH` | No | — | Google service account JSON |
| `GSC_SITE_URL` | No | — | GSC property (`sc-domain:` or `https://`) |
| `GA4_PROPERTY_ID` | No | — | Numeric GA4 property |
| `BROWSERLESS_API_KEY` | No | — | Cloud browser fallback |
| `API_AUTH_KEY` | No | — | API authentication (set in production) |
| `SSL_CERTFILE` / `SSL_KEYFILE` | No | — | TLS certificate paths |

Full list in `.env.example`.

## Deployment

```bash
# Generate self-signed cert (dev/staging)
python scripts/setup_ssl.py

# Start with HTTPS
SSL_CERTFILE=cert.pem SSL_KEYFILE=key.pem python -m api.main

# Docker
docker compose up -d

# Docker (with HTTPS certs mounted)
docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d
```

For production, deploy behind a TLS-terminating reverse proxy (Caddy, Nginx, Cloudflare).

## Testing

```bash
pytest tests/ -q          # 258 tests, 6 skipped (need API keys)
pytest tests/test_security.py -v   # 49 security-specific tests
```

## License

MIT
