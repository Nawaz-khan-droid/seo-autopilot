"""Structured error taxonomy for the SEO Autopilot API.

Provides a hierarchy of typed errors so clients can distinguish retryable vs
fatal failures, and monitoring can alert on specific failure modes.

All public API endpoints should raise ``HTTPException`` subclasses defined
here, which include an ``X-Error-Code`` response header.
"""
from __future__ import annotations

from fastapi import HTTPException
from starlette.responses import Response
from starlette.requests import Request


# ── Error codes ──

class AppError(HTTPException):
    """Base exception for all application-level errors.

    Every subclass sets ``status_code``, ``detail``, and ``error_code``.
    """

    error_code: str = "UNKNOWN"
    retryable: bool = False
    severity: str = "error"

    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=self.status_code,  # type: ignore[attr-defined]
            detail=detail or self.detail,  # type: ignore[attr-defined]
            headers={"X-Error-Code": self.error_code},
        )


class RateLimitError(AppError):
    status_code = 429
    detail = "Rate limit exceeded"
    error_code = "RATE_LIMITED"
    retryable = True
    severity = "warn"


class AuditTimeoutError(AppError):
    status_code = 504
    detail = "Audit timed out"
    error_code = "AUDIT_TIMEOUT"
    retryable = True
    severity = "warn"


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    retryable = False
    severity = "warn"


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    retryable = False
    severity = "info"


class AuthError(AppError):
    status_code = 401
    error_code = "UNAUTHORIZED"
    retryable = False
    severity = "warn"


class ProviderUnavailable(AppError):
    status_code = 502
    error_code = "PROVIDER_UNAVAILABLE"
    retryable = True
    severity = "error"


class DataUnavailable(AppError):
    status_code = 503
    error_code = "DATA_UNAVAILABLE"
    retryable = False
    severity = "warn"


# ── Request ID middleware ──

import uuid
import logging

logger = logging.getLogger(__name__)

_REQUEST_ID_CTX: str | None = None


def current_request_id() -> str | None:
    """Return the request ID for the current request, or None."""
    return _REQUEST_ID_CTX


class RequestIDMiddleware:
    """ASGI middleware that injects an ``X-Request-ID`` header.

    If the client sends an ``X-Request-ID`` header, it is forwarded through
    the system. Otherwise a new UUID is generated. The ID is available via
    ``current_request_id()`` for correlation across log lines.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        req_id: str | None = None

        for key, val in headers:
            if key == b"x-request-id":
                req_id = val.decode("utf-8", errors="replace").strip()
                break

        if not req_id:
            req_id = str(uuid.uuid4())

        global _REQUEST_ID_CTX
        _REQUEST_ID_CTX = req_id

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                new_headers = list(message.get("headers", []))
                new_headers.append((b"X-Request-ID", req_id.encode()))
                message["headers"] = new_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            _REQUEST_ID_CTX = None
