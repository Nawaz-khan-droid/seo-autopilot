"""Error resolver — classifies runtime failures and provides structured recovery.

Every function in the audit workflow that hits a known failure mode
should route through ``resolve_error()`` to get a consistent error
code, message, severity, and recovery action.

Usage::

    from api.error_resolver import resolve_error, AuditError

    result = resolve_error(
        source="playwright_headless",
        exception=e,
        context={"url": url},
    )
    if result.should_abort:
        raise AuditError(result.message)

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    FATAL = "fatal"        # Pipeline cannot continue
    HIGH = "high"          # Current step failed, fallback available
    MEDIUM = "medium"      # Non-critical feature degraded
    LOW = "low"            # Cosmetic / nice-to-have


class ErrorCode(Enum):
    # ── API / Auth ──
    API_KEY_MISSING = "API_KEY_MISSING"
    AUTH_DENIED = "AUTH_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    API_ERROR = "API_ERROR"

    # ── Network ──
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    TIMEOUT = "TIMEOUT"
    DNS_FAILURE = "DNS_FAILURE"
    HTTP_ERROR = "HTTP_ERROR"
    SSL_ERROR = "SSL_ERROR"

    # ── Browser ──
    PLAYWRIGHT_UNAVAILABLE = "PLAYWRIGHT_UNAVAILABLE"
    BROWSER_LAUNCH_FAILED = "BROWSER_LAUNCH_FAILED"
    PAGE_GOTO_FAILED = "PAGE_GOTO_FAILED"
    SCREENSHOT_FAILED = "SCREENSHOT_FAILED"
    CAPTCHA_BLOCKED = "CAPTCHA_BLOCKED"

    # ── Data ──
    PARSE_FAILED = "PARSE_FAILED"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    CORRUPT_CACHE = "CORRUPT_CACHE"
    MISSING_FIELD = "MISSING_FIELD"
    DATA_INCONSISTENCY = "DATA_INCONSISTENCY"

    # ── File I/O ──
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    DISK_FULL = "DISK_FULL"

    # ── Import ──
    MODULE_MISSING = "MODULE_MISSING"

    # ── LLM ──
    LLM_EMPTY = "LLM_EMPTY"
    LLM_HALLUCINATION = "LLM_HALLUCINATION"
    LLM_PARSE_FAILED = "LLM_PARSE_FAILED"

    # ── Catch-all ──
    UNKNOWN = "UNKNOWN"


@dataclass
class ErrorResult:
    code: ErrorCode
    severity: ErrorSeverity
    message: str
    should_abort: bool = False
    should_retry: bool = False
    fallback_action: str | None = None
    source: str = ""
    context: dict[str, Any] = field(default_factory=dict)


# ── Registry: known error signatures → structured result ──

def _classify(exception: BaseException, source: str = "", context: dict | None = None) -> ErrorResult:
    ctx = context or {}
    msg = str(exception)
    etype = type(exception).__name__

    # --- Auth / Keys ---
    if "api_key" in msg.lower() or "SERPAPI_KEY" in msg or "API key" in msg:
        return ErrorResult(ErrorCode.API_KEY_MISSING, ErrorSeverity.HIGH,
                           f"{source}: API key missing — skipping", source=source, context=ctx)
    if "401" in msg or "Unauthorized" in msg or "403" in msg or "Forbidden" in msg:
        if "gsc" in source.lower() or "search_console" in source.lower():
            return ErrorResult(ErrorCode.AUTH_DENIED, ErrorSeverity.MEDIUM,
                               "GSC: Access Required — add service account email to GSC property",
                               source=source, context=ctx)
        return ErrorResult(ErrorCode.AUTH_DENIED, ErrorSeverity.HIGH,
                           f"{source}: authentication failed", source=source, context=ctx)

    # --- Rate limiting ---
    if "429" in msg or "rate_limited" in msg or "quota" in msg.lower():
        return ErrorResult(ErrorCode.RATE_LIMITED, ErrorSeverity.MEDIUM,
                           f"{source}: rate limited", should_retry=True,
                           fallback_action="Wait and retry, or use cached fallback",
                           source=source, context=ctx)

    # --- Network ---
    if "ConnectionRefusedError" in etype or "Connection refused" in msg or "ECONNREFUSED" in msg:
        return ErrorResult(ErrorCode.CONNECTION_REFUSED, ErrorSeverity.HIGH,
                           f"{source}: connection refused", source=source, context=ctx)
    if "Timeout" in etype or "timeout" in msg.lower() or "TimeoutError" in etype or "timed out" in msg.lower():
        return ErrorResult(ErrorCode.TIMEOUT, ErrorSeverity.MEDIUM,
                           f"{source}: timeout", should_retry=True,
                           fallback_action="Retry or use cached data",
                           source=source, context=ctx)
    if "NameResolutionError" in etype or "getaddrinfo" in msg.lower() or "Name or service not known" in msg:
        return ErrorResult(ErrorCode.DNS_FAILURE, ErrorSeverity.HIGH,
                           f"{source}: DNS resolution failed for {ctx.get('url', '?')}",
                           source=source, context=ctx)
    if "SSLError" in etype or "CERTIFICATE_VERIFY_FAILED" in msg:
        return ErrorResult(ErrorCode.SSL_ERROR, ErrorSeverity.HIGH,
                           f"{source}: SSL certificate verification failed", source=source, context=ctx)
    if "HTTPStatusError" in etype or "httpx.HTTPStatusError" in etype or (hasattr(exception, 'status_code') and exception.status_code):
        code = getattr(exception, 'status_code', 0) or getattr(getattr(exception, 'response', None), 'status_code', 0)
        if 500 <= code < 600:
            return ErrorResult(ErrorCode.HTTP_ERROR, ErrorSeverity.MEDIUM,
                               f"{source}: HTTP {code}", should_retry=True, source=source, context=ctx)

    # --- Browser / Playwright ---
    if "playwright" in source.lower():
        if "Playwright" in msg or "playwright" in etype.lower():
            return ErrorResult(ErrorCode.PLAYWRIGHT_UNAVAILABLE, ErrorSeverity.HIGH,
                               f"{source}: Playwright not available", source=source, context=ctx)
    if "browser" in msg.lower() and ("launch" in msg.lower() or "connect" in msg.lower()):
        return ErrorResult(ErrorCode.BROWSER_LAUNCH_FAILED, ErrorSeverity.HIGH,
                           f"{source}: browser launch failed", source=source, context=ctx)
    if "goto" in msg.lower() and ("timeout" in msg.lower() or "failed" in msg.lower()):
        return ErrorResult(ErrorCode.PAGE_GOTO_FAILED, ErrorSeverity.MEDIUM,
                           f"{source}: page navigation failed", should_retry=True, source=source, context=ctx)
    if "CAPTCHA" in msg or "captcha" in msg.lower() or "blocked" in msg.lower():
        return ErrorResult(ErrorCode.CAPTCHA_BLOCKED, ErrorSeverity.HIGH,
                           f"{source}: CAPTCHA or block detected", source=source, context=ctx)

    # --- Data ---
    if "not found" in msg.lower() or "NotFound" in etype:
        return ErrorResult(ErrorCode.FILE_NOT_FOUND, ErrorSeverity.MEDIUM,
                           f"{source}: resource not found", source=source, context=ctx)
    if "PermissionError" in etype or "permission" in msg.lower():
        return ErrorResult(ErrorCode.PERMISSION_DENIED, ErrorSeverity.HIGH,
                           f"{source}: permission denied — file may be open in another program",
                           fallback_action="Close file and retry",
                           source=source, context=ctx)
    if "JSONDecode" in etype or "json.decoder" in etype:
        return ErrorResult(ErrorCode.CORRUPT_CACHE, ErrorSeverity.MEDIUM,
                           f"{source}: corrupt JSON cache — resetting", source=source, context=ctx)
    if "ModuleNotFoundError" in etype or "ImportError" in etype:
        return ErrorResult(ErrorCode.MODULE_MISSING, ErrorSeverity.HIGH,
                           f"{source}: required module missing — {msg.split()[-1] if msg else '?'}",
                           fallback_action="Install missing package: pip install <package>",
                           source=source, context=ctx)
    if "UnboundLocalError" in etype:
        return ErrorResult(ErrorCode.DATA_INCONSISTENCY, ErrorSeverity.FATAL,
                           f"{source}: variable scope bug — local import shadows global",
                           should_abort=True, source=source, context=ctx)
    if "KeyError" in etype:
        return ErrorResult(ErrorCode.MISSING_FIELD, ErrorSeverity.MEDIUM,
                           f"{source}: missing key {msg}", source=source, context=ctx)

    # --- LLM ---
    if "empty" in msg.lower() and ("content" in msg.lower() or "response" in msg.lower()):
        return ErrorResult(ErrorCode.LLM_EMPTY, ErrorSeverity.LOW,
                           f"{source}: LLM returned empty content", source=source, context=ctx)

    # --- Catch-all ---
    return ErrorResult(ErrorCode.UNKNOWN, ErrorSeverity.MEDIUM,
                       f"{source}: {msg}", source=source, context=ctx)


def resolve_error(
    source: str,
    exception: BaseException | None = None,
    context: dict | None = None,
    *,
    message: str = "",
    severity_override: ErrorSeverity | None = None,
    force_abort: bool = False,
) -> ErrorResult:
    """Classify a runtime error and return a structured ``ErrorResult``.

    Parameters
    ----------
    source : str
        Short identifier of the failing component (e.g. ``"playwright_headless"``).
    exception : BaseException | None
        The caught exception (used for classification).
    context : dict | None
        Extra key-value pairs for diagnostics (e.g. ``{"url": url}``).
    message : str
        Override the auto-generated message.
    severity_override : ErrorSeverity | None
        Force a severity (overrides auto-classification).
    force_abort : bool
        Treat this error as fatal regardless of classification.
    """
    ctx = context or {}
    if exception is not None:
        result = _classify(exception, source=source, context=ctx)
    else:
        result = ErrorResult(ErrorCode.UNKNOWN, ErrorSeverity.MEDIUM,
                             message or f"{source}: unspecified error",
                             source=source, context=ctx)

    if message:
        result.message = f"{source}: {message}"
    if severity_override:
        result.severity = severity_override
    if force_abort:
        result.should_abort = True

    level = {
        ErrorSeverity.FATAL: logger.critical,
        ErrorSeverity.HIGH: logger.error,
        ErrorSeverity.MEDIUM: logger.warning,
        ErrorSeverity.LOW: logger.info,
    }.get(result.severity, logger.warning)

    level("%s [%s] %s", result.source, result.code.value, result.message)
    return result


# ── Handy decorator for wrapping functions ──

def fallback_on_error(default_return: Any = None, *, source: str = "", abort_on: set[ErrorCode] | None = None):
    """Decorator: catch exceptions from the wrapped function, log via
    ``resolve_error``, and return ``default_return`` instead of raising.

    If the error code is in ``abort_on``, the original exception is re-raised.
    """
    from functools import wraps

    abort_on = abort_on or set()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            src = source or func.__name__
            try:
                return func(*args, **kwargs)
            except Exception as e:
                result = resolve_error(source=src, exception=e, context={"args": args, "kwargs": kwargs})
                if result.code in abort_on:
                    raise
                return default_return
        return wrapper
    return decorator


class AuditError(RuntimeError):
    """Raised when a pipeline error is severe enough to abort the audit."""
    pass
