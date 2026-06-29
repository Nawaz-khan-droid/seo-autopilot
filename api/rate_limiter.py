"""Rate limiter — Redis-backed with in-memory fallback.

Uses local Redis (``REDIS_URL``) or Upstash Redis REST API when available,
falls back to a process-local sliding-window limiter. This prevents DoS
bypass when running multiple uvicorn workers.

Usage:
    from api.rate_limiter import rate_limiter

    if not rate_limiter.check(client_ip):
        raise HTTPException(429, "Rate limit exceeded")
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_MAX_REQUESTS = 10
DEFAULT_WINDOW_SECONDS = 60


class RateLimiter:
    """Sliding-window rate limiter per IP.

    Backend selection:
      1. Local Redis (``redis-py``) if ``REDIS_URL`` is set
      2. Upstash Redis REST API if ``UPSTASH_REDIS_URL`` + ``UPSTASH_REDIS_TOKEN`` set
      3. In-memory dict (process-local, single-worker only)
    """

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS, window_seconds: int = DEFAULT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window = window_seconds
        self._upstash_url = ""
        self._upstash_token = ""
        self._redis_available = False
        self._redis_client: Any = None
        self._mode = "memory"
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._init_backend()

    def _init_backend(self):
        redis_url = os.environ.get("REDIS_URL", "")
        upstash_url = os.environ.get("UPSTASH_REDIS_URL", "")
        upstash_token = os.environ.get("UPSTASH_REDIS_TOKEN", "")

        if redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis_client = aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                )
                self._mode = "redis"
                self._redis_available = True
                logger.info("Rate limiter: using local Redis (%s)", redis_url)
                return
            except Exception as e:
                logger.warning("Rate limiter: local Redis unavailable (%s)", e)

        if upstash_url and upstash_token:
            self._upstash_url = upstash_url.rstrip("/")
            self._upstash_token = upstash_token
            self._mode = "upstash"
            logger.info("Rate limiter: using Upstash Redis REST API")
            return

        logger.info("Rate limiter: using in-memory backend (per-process, not for multi-worker)")

    def check(self, ip: str) -> bool:
        if self._mode == "redis":
            return self._check_redis(ip)
        elif self._mode == "upstash":
            return self._check_upstash(ip)
        return self._check_memory(ip)

    # ── Local Redis (redis-py) ──

    def _check_redis(self, ip: str) -> bool:
        try:
            import redis.asyncio as aioredis
            key = f"ratelimit:{ip}"
            now = time.time()
            cutoff = now - self.window

            pipe = self._redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, self.window + 10)
            _, count, _, _ = pipe.execute()

            return int(count) < self.max_requests
        except Exception as e:
            logger.warning("Redis rate limiter failed: %s — falling back to in-memory", e)
            self._mode = "memory"
            return self._check_memory(ip)

    # ── Upstash Redis (REST API) ──

    def _check_upstash(self, ip: str) -> bool:
        try:
            key = f"ratelimit:{ip}"
            now = time.time()
            cutoff = now - self.window

            # Remove expired entries
            httpx.post(
                f"{self._upstash_url}/zremrangebyscore/{key}/{cutoff}/{now}",
                headers={"Authorization": f"Bearer {self._upstash_token}"},
                timeout=1.0,
            )
            # Count remaining
            resp = httpx.get(
                f"{self._upstash_url}/zcard/{key}",
                headers={"Authorization": f"Bearer {self._upstash_token}"},
                timeout=1.0,
            )
            count = int(resp.text or "0")
            if count >= self.max_requests:
                return False
            # Add current request
            httpx.post(
                f"{self._upstash_url}/zadd/{key}/{now}/{now}",
                headers={"Authorization": f"Bearer {self._upstash_token}"},
                timeout=1.0,
            )
            httpx.post(
                f"{self._upstash_url}/expire/{key}/{self.window + 10}",
                headers={"Authorization": f"Bearer {self._upstash_token}"},
                timeout=1.0,
            )
            return True
        except Exception as e:
            logger.warning("Upstash rate limiter failed: %s — falling back to in-memory", e)
            self._mode = "memory"
            return self._check_memory(ip)

    # ── In-memory fallback ──

    def _check_memory(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        bucket = self._buckets[ip]
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


# Module-level singleton
rate_limiter = RateLimiter()
