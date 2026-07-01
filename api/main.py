"""FastAPI backend — wraps report generator, reads real data from cache or sheets.

Endpoints:
  POST /api/reports/generate  → generate + download DOCX file(s)
  GET  /api/clients           → list known clients from client_context.py
  GET  /api/health            → health check

Data sources (in priority order):
  1. Google Sheets (if SHEET_NAME + credentials configured)
  2. JSON data cache (written by main.py Phase 6)
  3. → Returns 503 if neither is available (no fake data)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from contextlib import asynccontextmanager
from filelock import FileLock

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.errors import (
    AppError, RateLimitError, AuditTimeoutError, ValidationError,
    NotFoundError, AuthError, ProviderUnavailable, DataUnavailable,
    RequestIDMiddleware, current_request_id,
)
from api.browser_manager import close_all_browsers
from api.rate_limiter import rate_limiter
from config.sheet_schema import TabName, TAB_TO_KEY
from modules.http_pool import sync_client, async_client, close_clients
from modules.logger_config import setup_logging

setup_logging(level=logging.INFO)

from config.settings import (
    API_AUTH_KEY, CORS_ORIGINS, CREDENTIALS_PATH, GROQ_API_KEY, SHEET_NAME,
)
from report.client_context import CLIENT_PROFILES, get_client_keywords
from report.docx_action_plan import build_action_plan_docx
from report.docx_report import build_clients_report
from report.docx_technical_audit import build_technical_audit

logger = logging.getLogger(__name__)

@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    logger.info("Shutting down — closing HTTP connections and Playwright browsers")
    await close_clients()
    close_all_browsers()


app = FastAPI(
    title="SEO Autopilot API",
    version="1.0.0",
    description="Generate client-ready SEO reports and internal action plans.",
    lifespan=_lifespan,
)

# Parse CORS origins from env (comma-separated), filter empties
_ALLOWED_ORIGINS = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
# Always allow Vercel domains (production + preview deployments)
_VERCEL_REGEX = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=_VERCEL_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID middleware — injected before all other middleware ──

app.add_middleware(RequestIDMiddleware)


# ── API Key Authentication Middleware ──

class APIKeyMiddleware(BaseHTTPMiddleware):
    """Require X-API-Key header on all /api/ routes when API_AUTH_KEY is set.

    Uses timing-safe comparison (hmac.compare_digest) to prevent
    timing-based brute-force of the API key.
    Skips auth on GET /api/health (health checks need no key) and on
    OPTIONS preflight requests.
    """

    async def dispatch(self, request: Request, call_next):
        if not API_AUTH_KEY:
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path == "/api/health":
            return await call_next(request)
        if path.startswith("/api/"):
            api_key = request.headers.get("x-api-key", "")
            if not hmac.compare_digest(api_key, API_AUTH_KEY):
                raise AuthError("Unauthorized — provide X-API-Key header")
        return await call_next(request)


app.add_middleware(APIKeyMiddleware)

if not API_AUTH_KEY:
    logger.warning(
        "API_AUTH_KEY is not set — all /api/ endpoints are publicly accessible. "
        "Set API_AUTH_KEY in .env for production."
    )


# ── Background job store (for long-running audits behind Codespaces proxy) ──

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()

def _job_set(job_id: str, **kwargs: Any) -> None:
    with _jobs_lock:
        _jobs[job_id] = {**_jobs.get(job_id, {}), **kwargs, "updated_at": time.time()}

def _job_get(job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        return _jobs.get(job_id)

def _job_cleanup() -> None:
    cutoff = time.time() - 3600
    with _jobs_lock:
        if len(_jobs) > 500:
            stale = sorted(_jobs.keys(), key=lambda k: _jobs[k].get("updated_at", 0))[:-200]
            for k in stale:
                del _jobs[k]
        stale = [k for k, v in _jobs.items() if v.get("updated_at", 0) < cutoff]
        for k in stale:
            del _jobs[k]


# ── Idempotency cache (JSON, 1h TTL) ──

_IDEMPOTENCY_DIR = Path(__file__).resolve().parent.parent / "output" / "idempotency"
_IDEMPOTENCY_DIR.mkdir(parents=True, exist_ok=True)
_IDEMPOTENCY_TTL = 3600


def _idempotency_key_path(key: str) -> Path:
    safe = hashlib.sha256(key.encode()).hexdigest()[:32]
    return _IDEMPOTENCY_DIR / f"{safe}.json"


def _get_idempotent_result(key: str) -> dict[str, Any] | None:
    path = _idempotency_key_path(key)
    lock_path = path.with_suffix(".lock")
    lock = FileLock(str(lock_path), timeout=1.0)
    try:
        with lock:
            if not path.exists():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) > _IDEMPOTENCY_TTL:
                path.unlink(missing_ok=True)
                return None
            logger.info("Idempotency hit for key=%s", key[:16])
            return data.get("result")
    except Exception:
        return None


def _set_idempotent_result(key: str, result: dict[str, Any]) -> None:
    path = _idempotency_key_path(key)
    lock_path = path.with_suffix(".lock")
    lock = FileLock(str(lock_path), timeout=1.0)
    try:
        with lock:
            path.write_text(
                json.dumps({"ts": time.time(), "result": result}, default=str),
                encoding="utf-8",
            )
    except Exception as e:
        logger.debug("Idempotency cache write failed: %s", e)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _extract_rankings_for_cache(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract ranking rows from audit result for cache storage."""
    return result.get("rankings", [])

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "seo-report-frontend"
FRONTEND_DIR.mkdir(exist_ok=True)
(FRONTEND_DIR / "css").mkdir(exist_ok=True)
(FRONTEND_DIR / "js").mkdir(exist_ok=True)

UPLOAD_DIR = OUTPUT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ── Request validation ──

_PRIVATE_HOST_PREFIXES = (
    "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.",
    "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.",
    "172.29.", "172.30.", "172.31.", "192.168.", "169.254.", "fd", "fc",
)
_METADATA_HOSTS = {
    "169.254.169.254", "metadata.google.internal", "metadata.internal",
    "100.100.100.204", "100.100.100.200",
}


def _validate_url_not_private(url: str):
    """Raise ValidationError if URL points to a private/internal host."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValidationError("Invalid URL: no hostname")
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]") or host in _METADATA_HOSTS:
        raise ValidationError("Invalid URL: private/internal hosts are not allowed")
    if any(host.startswith(p) for p in _PRIVATE_HOST_PREFIXES):
        raise ValidationError("Invalid URL: private/internal hosts are not allowed")


def _sanitize_filename_component(s: str) -> str:
    s = s.replace("..", "").replace("/", "").replace("\\", "").replace(":", "")
    return s.strip(" .-_")


def _validate_generate_request(body: dict[str, Any]) -> dict[str, Any]:
    client = (body.get("client_name") or "").strip()
    if not client:
        raise ValidationError("client_name is required")
    client = _sanitize_filename_component(client)
    if not client:
        raise ValidationError("client_name contains only invalid characters")
    month = (body.get("report_month") or "").strip() or datetime.now().strftime("%B %Y")
    deliverable = (body.get("type") or "both").strip().lower()
    if deliverable not in ("both", "report", "plan"):
        deliverable = "both"
    return {"client_name": client, "report_month": month, "type": deliverable}


# ── Data loader — real data only, no hardcoded fallbacks ──

def _load_sheet_data() -> dict[str, list[dict[str, Any]]] | None:
    """Load raw data from Google Sheets if configured and available."""
    if not SHEET_NAME or not CREDENTIALS_PATH:
        logger.info("Sheet not configured (SHEET_NAME or CREDENTIALS_PATH missing)")
        return None
    creds_path = Path(CREDENTIALS_PATH)
    if not creds_path.exists():
        logger.info("Sheet credentials not found at %s", CREDENTIALS_PATH)
        return None
    try:
        from modules.sheet_client import SheetClient
        sheet = SheetClient(credentials_path=str(creds_path), sheet_name=SHEET_NAME)
    except Exception as e:
        logger.warning("SheetClient init failed: %s", e)
        return None

    result: dict[str, list[dict[str, Any]]] = {}
    for tab_name, key in TAB_TO_KEY.items():
        try:
            result[key] = sheet.read_records(tab_name.value)
        except Exception as e:
            logger.debug("Could not read tab '%s': %s", tab_name.value, e)
            result[key] = []
    if not any(result.values()):
        logger.warning("All sheet tabs returned empty data")
        return None
    return result


def _load_cache_data() -> dict[str, list[dict[str, Any]]] | None:
    """Load raw data from JSON cache (written by main.py Phase 6)."""
    try:
        from api.data_cache import load_sheet_data
        tabs = load_sheet_data()
        if not tabs:
            return None
    except Exception as e:
        logger.warning("Data cache load failed: %s", e)
        return None

    result: dict[str, list[dict[str, Any]]] = {}
    for tab_name, key in TAB_TO_KEY.items():
        result[key] = tabs.get(tab_name.value, [])
    return result


def _load_raw_data() -> dict[str, list[dict[str, Any]]]:
    """Load data: sheets first, cache fallback. Returns empty dict if neither."""
    data = _load_sheet_data()
    if data:
        logger.info("Data source: Google Sheets")
        return data
    data = _load_cache_data()
    if data:
        logger.info("Data source: JSON cache")
        return data
    logger.error("No data source available — sheets not configured and no cache found")
    return {}


def _build_facts(client_name: str, month: str, raw_data: dict[str, list[dict[str, Any]]]) -> object:
    """Build ReportFacts from raw data. Raises HTTPException if data is empty."""
    from report.facts_loader import build_facts

    keywords_raw = raw_data.get("keywords_raw", [])
    rankings_raw = raw_data.get("rankings_raw", [])
    history_raw = raw_data.get("history_raw", [])
    ai_raw = raw_data.get("ai_raw", [])
    audit_raw = raw_data.get("audit_raw", [])
    insights_raw = raw_data.get("insights_raw", [])
    plan_raw = raw_data.get("plan_raw", [])
    competitor_raw = raw_data.get("competitor_raw", [])

    # Allow report generation even without ranking data — show what we have
    if not rankings_raw and not history_raw and not audit_raw:
        raise HTTPException(503, "No data available. Run an audit first via /api/demo/generate or /api/audit/run.")

    facts = build_facts(
        keywords_raw=keywords_raw,
        rankings_raw=rankings_raw,
        history_raw=history_raw,
        ai_raw=ai_raw,
        audit_raw=audit_raw,
        insights_raw=insights_raw,
        plan_raw=plan_raw,
        competitor_raw=competitor_raw,
        report_month=month,
        agency_name="SEO Agency",
        client_name=client_name,
    )
    return facts


# ── Endpoints ──

# Required columns for backlink CSV — at least one per row must match
_REQUIRED_BACKLINK_COLS: set[str] = {
    "total_backlinks", "ref_domains", "dofollow", "nofollow",
    "domain_rating", "dr", "da", "domain_authority",
}


def _validate_backlink_csv(content: bytes) -> int:
    """Validate backlink CSV content. Returns row count or raises ValidationError."""
    import csv
    import io
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("CSV must be UTF-8 encoded")
    try:
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception as e:
        raise ValidationError(f"Failed to parse CSV: {e}")
    if not reader.fieldnames:
        raise ValidationError("CSV has no header row")
    norm_headers = {
        h.strip().lower().replace(" ", "_").replace("-", "_")
        for h in reader.fieldnames if h
    }
    if not norm_headers:
        raise ValidationError("CSV headers are empty after normalisation")
    has_total = bool(norm_headers & {"total_backlinks", "backlinks_total", "backlinks", "total"})
    has_ref = bool(norm_headers & {"ref_domains", "referring_domains", "ref_domain", "referring_domain"})
    if not has_total or not has_ref:
        raise ValidationError(
            "CSV must have columns for total_backlinks and ref_domains "
            "(or common variants). Found headers: " + ", ".join(sorted(norm_headers)),
        )
    rows = list(reader)
    if not rows:
        raise ValidationError("CSV has no data rows")
    return len(rows)


@app.post("/upload-backlinks/{project_domain:path}")
async def upload_backlinks_csv(project_domain: str, file: UploadFile = File(...)):
    """Upload a backlink CSV for a domain. CSV must have columns:
    total_backlinks, ref_domains, dofollow, nofollow, domain_rating, source

    Validates headers, normalises encodings, and stores the file.
    The data is picked up automatically by the audit pipeline.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise ValidationError("Only .csv files are accepted")

    domain = project_domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/")[0]

    content = await file.read()
    row_count = _validate_backlink_csv(content)

    from modules.backlink_client import _csv_path as get_csv_path
    out = get_csv_path(domain)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content)

    logger.info(
        "Backlink CSV uploaded for %s -> %s (%d rows, %d bytes)",
        domain, out, row_count, len(content),
    )

    return {
        "status": "ok",
        "domain": domain,
        "path": str(out),
        "rows": row_count,
    }


@app.get("/api/health")
async def health():
    """Health check. groq_configured == False just means narrative is limited."""
    return {"status": "ok", "groq_configured": bool(GROQ_API_KEY), "request_id": current_request_id()}


@app.get("/api/clients")
async def list_clients():
    """List known client profiles from client_context.py."""
    result = []
    for name, profile in CLIENT_PROFILES.items():
        kw_count = len(get_client_keywords(name))
        result.append({
            "name": name.title(),
            "business_type": profile.get("business_type", "Unknown"),
            "website": profile.get("website", ""),
            "keyword_count": kw_count,
        })
    return {"clients": result}


@app.post("/api/reports/generate")
async def generate_report(body: dict[str, Any]):
    """Generate DOCX report(s) from real data. No hardcoded data."""
    params = _validate_generate_request(body)
    client_name = params["client_name"]
    month = params["report_month"]
    deliverable = params["type"]

    raw_data = _load_raw_data()
    if not raw_data:
        raise DataUnavailable(
            "No data available. Run the data pipeline (python main.py) to collect real data, "
            "or ensure Google Sheets / data cache is configured.",
        )

    facts = _build_facts(client_name, month, raw_data)

    client_slug = client_name.lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated: list[dict[str, Any]] = []
    errors: list[str] = []

    loop = asyncio.get_event_loop()

    if deliverable in ("both", "report"):
        try:
            filename = f"{client_name} Monthly SEO Report {month} {timestamp}.docx"
            filepath = str(OUTPUT_DIR / filename)
            await asyncio.wait_for(
                loop.run_in_executor(None, build_clients_report, facts, filepath),
                timeout=60.0,
            )
            generated.append({"type": "report", "filename": filename, "size_bytes": Path(filepath).stat().st_size})
        except asyncio.TimeoutError:
            errors.append("Report generation timed out")
        except Exception as e:
            logger.error("Report generation failed: %s", e, exc_info=True)
            errors.append(f"Client report: {e}")

    if deliverable in ("both", "plan"):
        try:
            filename = f"{client_name} SEO Action Plan {month} {timestamp}.docx"
            filepath = str(OUTPUT_DIR / filename)
            await asyncio.wait_for(
                loop.run_in_executor(None, build_action_plan_docx, facts, filepath),
                timeout=60.0,
            )
            generated.append({"type": "plan", "filename": filename, "size_bytes": Path(filepath).stat().st_size})
        except asyncio.TimeoutError:
            errors.append("Action plan generation timed out")
        except Exception as e:
            logger.error("Action plan generation failed: %s", e, exc_info=True)
            errors.append(f"Action plan: {e}")

    response: dict[str, Any] = {
        "success": len(generated) > 0,
        "client": client_name,
        "month": month,
        "generated": generated,
    }
    if generated:
        response["download_url"] = f"/api/reports/download/{generated[0]['filename']}"
    if errors:
        response["errors"] = errors

    try:
        from api.data_cache import cleanup_old_reports
        cleanup_old_reports(OUTPUT_DIR, keep_per_type=10)
    except Exception as e:
        logger.debug("Cleanup skipped: %s", e)

    return response


@app.get("/api/reports/download/{filename:path}")
async def download_report(filename: str):
    """Download a generated DOCX file (path-traversal safe)."""
    filepath = (OUTPUT_DIR / filename).resolve()
    if not str(filepath).startswith(str(OUTPUT_DIR.resolve())):
        raise ValidationError("Invalid path")
    if not filepath.exists():
        raise NotFoundError(f"Report not found: {filename}")
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(str(filepath), media_type=media_type, filename=filepath.name)


@app.post("/api/audit/run")
async def run_audit(body: dict[str, Any], request: Request):
    """Run a manual SEO audit on any URL. Optionally read client data from a shared sheet.

    Supports idempotency via ``Idempotency-Key`` header — repeat requests with
    the same key return the cached result for up to 1 hour (avoids double crawl).

    Request: { url, sheet_url?, mode? ("single"|"full"), report_month? }
    Response: { success, url, month, generated[{type, filename, size_bytes}], errors[] }
    """
    url = (body.get("url") or "").strip()
    if not url:
        raise ValidationError("url is required")
    if not url.startswith("http"):
        url = "https://" + url
    _validate_url_not_private(url)

    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip):
        raise RateLimitError("Rate limit exceeded — try again in 60 seconds")

    idempotency_key = request.headers.get("idempotency-key", "").strip()
    if idempotency_key:
        cached = _get_idempotent_result(idempotency_key)
        if cached is not None:
            return cached

    sheet_url = (body.get("sheet_url") or "").strip()
    mode = (body.get("mode") or "single").strip().lower()
    if mode not in ("single", "full"):
        mode = "single"
    report_month = (body.get("report_month") or "").strip() or datetime.now().strftime("%B %Y")

    from api.audit_workflow import run_audit as _run_audit
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_audit, url, sheet_url, mode, report_month),
            timeout=180.0,
        )
    except asyncio.TimeoutError:
        raise AuditTimeoutError("Audit timed out after 180 seconds")
    except Exception as e:
        logger.exception("Audit crashed for %s", url)
        raise ProviderUnavailable(f"Audit error: {e}")

    if not result.get("success") and result.get("errors"):
        raise ProviderUnavailable("; ".join(result["errors"]))

    if idempotency_key:
        _set_idempotent_result(idempotency_key, result)

    return result


# ── Demo endpoint — run audit on any URL (background job + polling) ──

def _run_demo_background(job_id: str, url: str) -> None:
    """Run the audit in a background thread so Codespaces proxy doesn't drop.
    Always returns at least quick-scan metrics (guaranteed, <5s).
    """
    from api.audit_workflow import _quick_page_scan, run_audit as _run_audit
    # Step 1: Quick scan (guaranteed, <5s) → store as initial result
    quick = _quick_page_scan(url)
    _quick_issues = []
    if quick.get("missing_h1_count", 0):
        _quick_issues.append({"page": url, "issue_text": "Missing H1 tag", "severity": "Warning"})
    if quick.get("missing_meta_tags", 0):
        _quick_issues.append({"page": url, "issue_text": "Missing meta description", "severity": "Warning"})
    if quick.get("missing_alt_tags", 0):
        _quick_issues.append({"page": url, "issue_text": f"{quick['missing_alt_tags']} images missing alt text", "severity": "Warning"})
    _job_set(job_id, status="done", progress="Scan complete — enriching...", result={
        "success": True,
        "client": url,
        "month": datetime.now().strftime("%B %Y"),
        "metrics": quick,
        "issues": _quick_issues,
        "niche": "—",
    })
    # Step 2: Full audit (may take 60-120s, may fail)
    try:
        result = _run_audit(url)
        full_metrics = result.get("metrics", {})
        # Merge: start from quick scan, then overlay non-empty full audit values.
        # This ensures full-audit enriched rankings/backlinks/CWV win over quick-scan zeros.
        enriched = dict(quick)
        for k, v in full_metrics.items():
            if v not in (None, 0, "", "No Data", "Data Pending"):
                enriched[k] = v

        # Bridge: write audit results to data cache so report endpoint can read them
        try:
            from api.data_cache import save_audit_results
            save_audit_results(
                url=url,
                month=datetime.now().strftime("%B %Y"),
                metrics=enriched,
                issues=result.get("issues", []),
                rankings=_extract_rankings_for_cache(result),
            )
        except Exception as cache_err:
            logger.debug("Cache write skipped: %s", cache_err)

        _job_set(job_id, status="done", result={
            "success": result.get("success", True),
            "client": result.get("client", url),
            "month": result.get("month", datetime.now().strftime("%B %Y")),
            "metrics": enriched,
            "issues": _quick_issues + result.get("issues", []),
            "niche": result.get("niche", "—"),
        })
    except Exception as e:
        logger.exception("Full audit failed for %s — returning quick scan", url)
        # Quick scan already stored — keep it


@app.post("/api/demo/generate")
async def demo_generate(payload: dict | None = None, request: Request = None):
    """Start a background audit job. Returns job_id immediately for polling."""
    if request and request.client:
        if not rate_limiter.check(request.client.host):
            raise RateLimitError("Rate limit exceeded — try again in 60 seconds")

    body = payload or {}
    url = body.get("url", "").strip() or "https://www.beautifulindia.com"
    _validate_url_not_private(url)

    job_id = uuid.uuid4().hex[:16]
    _job_cleanup()
    _job_set(job_id, status="queued", url=url, progress="Starting audit...")

    t = threading.Thread(target=_run_demo_background, args=(job_id, url), daemon=True)
    t.start()

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/demo/status/{job_id}")
async def demo_status(job_id: str):
    """Poll for background audit job result."""
    job = _job_get(job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found")
    if job["status"] == "done":
        return {"status": "done", "result": job["result"]}
    if job["status"] == "error":
        return {"status": "error", "error": job.get("error", "Unknown error")}
    return {"status": job["status"], "progress": job.get("progress", "")}


# ── File upload endpoint for monthly reports ──

@app.post("/api/reports/upload")
async def upload_report(file: UploadFile = File(...)):
    """Upload a CSV/JSON file with sheet data for monthly report generation."""
    if not file.filename:
        raise ValidationError("No file provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in (".csv", ".json"):
        raise ValidationError("Only .csv and .json files are accepted")

    MAX_UPLOAD = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_UPLOAD:
        raise ValidationError(f"File too large (max {MAX_UPLOAD // 1024 // 1024}MB)")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = UPLOAD_DIR / f"upload_{ts}{ext}"
    dest.write_bytes(content)
    return {"success": True, "filename": dest.name, "size_bytes": len(content), "path": f"/api/reports/download_upload/{dest.name}"}


@app.get("/api/reports/download_upload/{filename:path}")
async def download_upload(filename: str):
    filepath = (UPLOAD_DIR / filename).resolve()
    if not str(filepath).startswith(str(UPLOAD_DIR.resolve())):
        raise ValidationError("Invalid path")
    if not filepath.exists():
        raise NotFoundError()
    return FileResponse(str(filepath))


# ── Serve frontend SPA + static files ──

@app.get("/", include_in_schema=False)
async def serve_root():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        return HTMLResponse("<h1>Frontend not built yet.</h1>")
    return HTMLResponse(index.read_text(encoding="utf-8"))

@app.get("/{path:path}", include_in_schema=False)
async def serve_frontend(path: str):
    if path.startswith("api/") or path.startswith("docs") or path.startswith("openapi"):
        raise NotFoundError()
    static_file = (FRONTEND_DIR / path).resolve()
    if not str(static_file).startswith(str(FRONTEND_DIR.resolve())):
        raise NotFoundError()
    if static_file.exists() and static_file.is_file():
        media_types = {
            ".css": "text/css", ".js": "text/javascript", ".html": "text/html",
            ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
            ".ico": "image/x-icon", ".json": "application/json",
        }
        mt = media_types.get(static_file.suffix.lower(), "application/octet-stream")
        return FileResponse(str(static_file), media_type=mt)
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    raise NotFoundError()


# Graceful shutdown is handled by the _lifespan context manager above.


if __name__ == "__main__":
    import ssl
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    workers = int(os.environ.get("WEB_CONCURRENCY", "4"))
    ssl_certfile = os.environ.get("SSL_CERTFILE", "")
    ssl_keyfile = os.environ.get("SSL_KEYFILE", "")
    ssl_ctx = None
    if ssl_certfile and ssl_keyfile:
        cert_path = Path(ssl_certfile)
        key_path = Path(ssl_keyfile)
        if cert_path.exists() and key_path.exists():
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(str(cert_path), str(key_path))
            logger.info("HTTPS enabled with cert=%s key=%s", ssl_certfile, ssl_keyfile)
        else:
            logger.warning("SSL cert/key files not found — falling back to HTTP")
    if ssl_ctx is None:
        logger.warning(
            "Server running WITHOUT HTTPS. Set SSL_CERTFILE and SSL_KEYFILE env vars "
            "for TLS, or deploy behind a TLS-terminating reverse proxy (Caddy, Nginx, Cloudflare)."
        )
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, workers=workers, reload=False, ssl=ssl_ctx)
