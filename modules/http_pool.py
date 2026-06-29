"""Shared HTTPX clients with connection pooling.

All modules should import ``sync_client()`` or ``async_client()`` instead of
creating one-shot ``httpx.Client()`` / ``httpx.AsyncClient()`` instances.
This eliminates per-request TCP+TLS handshake overhead.

Usage:
    from modules.http_pool import sync_client, async_client

    # Synchronous
    resp = sync_client().get("https://example.com")

    # Async
    resp = await async_client().get("https://example.com")
"""
from __future__ import annotations

import logging

import httpx
from httpx import AsyncClient, Client, Limits, Timeout

logger = logging.getLogger(__name__)

_POOL_LIMITS = Limits(
    max_keepalive_connections=20,
    max_connections=100,
    keepalive_expiry=30.0,
)

_DEFAULT_TIMEOUT = Timeout(30.0, connect=10.0, read=20.0, pool=10.0)

_async_client: AsyncClient | None = None
_sync_client: Client | None = None


def sync_client() -> Client:
    """Return the shared synchronous HTTPX client (lazily initialized)."""
    global _sync_client
    if _sync_client is None:
        _sync_client = Client(limits=_POOL_LIMITS, timeout=_DEFAULT_TIMEOUT)
        logger.debug("HTTPX sync client initialized (pool=%d/%d, keepalive=%ds)",
                      _POOL_LIMITS.max_keepalive_connections,
                      _POOL_LIMITS.max_connections,
                      _POOL_LIMITS.keepalive_expiry)
    return _sync_client


def async_client() -> AsyncClient:
    """Return the shared asynchronous HTTPX client (lazily initialized)."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncClient(limits=_POOL_LIMITS, timeout=_DEFAULT_TIMEOUT)
        logger.debug("HTTPX async client initialized (pool=%d/%d, keepalive=%ds)",
                      _POOL_LIMITS.max_keepalive_connections,
                      _POOL_LIMITS.max_connections,
                      _POOL_LIMITS.keepalive_expiry)
    return _async_client


async def close_clients():
    """Close all shared HTTPX clients (call during graceful shutdown)."""
    global _async_client, _sync_client
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None
        logger.debug("HTTPX async client closed")
    if _sync_client is not None:
        _sync_client.close()
        _sync_client = None
        logger.debug("HTTPX sync client closed")
