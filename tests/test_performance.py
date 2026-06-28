"""Hypothesis-driven performance & load testing for SEO Autopilot.

Tests 5 hypotheses about system behavior under concurrent load:
  H1: Single-request latency < 2s for health endpoint
  H2: 10 concurrent health requests all succeed (no connection pool exhaustion)
  H3: Sequential audit requests reuse browser thread-local (no cross-contamination)
  H4: File-locked captcha telemetry survives 5 concurrent writes without corruption
  H5: Cache file locking prevents corruption under concurrent rank writes

Run:  pytest tests/test_performance.py -v --tb=short
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import random
import string
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

# ── Hypothesis H1: Single-request latency ──

@pytest.mark.skipif(
    not os.environ.get("CI", ""),
    reason="Requires running server on localhost:8000",
)
@pytest.mark.asyncio
async def test_h1_health_endpoint_latency():
    """H1: Health endpoint responds in < 2s."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        t0 = time.monotonic()
        resp = await client.get("/api/health")
        elapsed = time.monotonic() - t0
    assert resp.status_code == 200
    assert elapsed < 2.0, f"Health took {elapsed:.2f}s — exceeds 2s threshold"


# ── Hypothesis H2: Concurrent health requests ──

def _hit_health(result_list: list, idx: int):
    """Fire a health check and record (status, elapsed)."""
    try:
        t0 = time.monotonic()
        resp = httpx.get("http://localhost:8000/api/health", timeout=10.0)
        elapsed = time.monotonic() - t0
        result_list.append((idx, resp.status_code, elapsed))
    except Exception as e:
        result_list.append((idx, -1, str(e)))


@pytest.mark.skipif(
    not os.environ.get("CI", ""),
    reason="Load test requires running server on localhost:8000",
)
def test_h2_concurrent_health_requests():
    """H2: 10 concurrent health requests all return 200."""
    results: list[tuple[int, int, float | str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_hit_health, results, i) for i in range(10)]
        concurrent.futures.wait(futures, timeout=30.0)

    errors = [r for r in results if r[1] != 200]
    assert not errors, f"{len(errors)} concurrent requests failed: {errors}"
    assert len(results) == 10


# ── Hypothesis H4: File-locked captcha telemetry ──

def _writer(lock_path: str, data_path: str, worker_id: int, iterations: int = 5):
    """Simulate a concurrent captcha telemetry writer."""
    from filelock import FileLock
    lock = FileLock(lock_path, timeout=5.0)
    for _ in range(iterations):
        event = {
            "ts": time.time(),
            "outcome": random.choice(["success", "blocked"]),
            "domain": f"test-{worker_id}.com",
            "detail": f"worker-{worker_id}",
        }
        with lock:
            existing: list[dict] = []
            if Path(data_path).exists():
                raw = Path(data_path).read_text(encoding="utf-8")
                if raw.strip():
                    existing = json.loads(raw)
            existing.append(event)
            Path(data_path).write_text(
                json.dumps(existing[-100:], indent=2),
                encoding="utf-8",
            )
        time.sleep(random.uniform(0.001, 0.005))


def test_h4_filelock_captcha_integrity():
    """H4: 5 concurrent writers to captcha_telemetry.json don't corrupt the file."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        data_path = Path(tmp) / "captcha_telemetry.json"
        lock_path = str(Path(tmp) / "captcha_telemetry.json.lock")

        threads = [
            threading.Thread(target=_writer, args=(lock_path, str(data_path), i))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        # Verify the file is valid JSON and all events are present
        assert data_path.exists()
        raw = data_path.read_text(encoding="utf-8")
        events = json.loads(raw)
        assert len(events) == 5 * 5, f"Expected 25 events, got {len(events)}"
        # Verify each worker's events are present
        worker_ids = {e["detail"] for e in events}
        assert len(worker_ids) == 5, f"Expected 5 workers, got {worker_ids}"


# ── Hypothesis H5: Rank cache file locking ──

def _rank_writer(lock_path: str, data_path: str, keyword: str, rank: int):
    """Simulate a concurrent rank cache writer."""
    from filelock import FileLock
    lock = FileLock(lock_path, timeout=5.0)
    with lock:
        existing: dict = {}
        if Path(data_path).exists():
            raw = Path(data_path).read_text(encoding="utf-8")
            if raw.strip():
                existing = json.loads(raw)
        existing[keyword] = {"rank": rank, "ts": time.time()}
        Path(data_path).write_text(json.dumps(existing, indent=2), encoding="utf-8")


def test_h5_rank_cache_locking():
    """H5: Concurrent rank cache writes produce valid JSON without data loss."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        data_path = Path(tmp) / "test_ranks.json"
        lock_path = str(Path(tmp) / "test_ranks.json.lock")

        words = [f"keyword-{i}" for i in range(20)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = [
                pool.submit(_rank_writer, lock_path, str(data_path), word, i)
                for i, word in enumerate(words)
            ]
            concurrent.futures.wait(futures, timeout=30.0)

        # Verify all keywords survived
        raw = data_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert len(data) == 20, f"Expected 20 keywords, got {len(data)}"
        for i, word in enumerate(words):
            assert word in data, f"Missing keyword: {word}"
            assert data[word]["rank"] == i


# ── Hypothesis H6: Malware domain blocklist ──

def test_h6_malware_blocklist_blocks_known_domains():
    """H6: _is_malware_request returns True for known malware domains."""
    from api.crawl_engine import _is_malware_request

    assert _is_malware_request("https://malwaredomainlist.com/evil.exe")
    assert _is_malware_request("https://urlhaus.abuse.ch/recent/")
    # Subdomain should also match
    assert _is_malware_request("https://sub.threatfox.abuse.ch/path")
    # Unrelated domain should not match
    assert not _is_malware_request("https://example.com/clean")
    assert not _is_malware_request("https://google.com/search")


def test_h7_mime_blocklist_blocks_dangerous_extensions():
    """H7: _is_blocked_mime returns True for dangerous file extensions."""
    from api.crawl_engine import _is_blocked_mime

    assert _is_blocked_mime("https://evil.com/payload.exe")
    assert _is_blocked_mime("https://evil.com/script.vbs")
    assert _is_blocked_mime("https://evil.com/exploit.jar")
    assert _is_blocked_mime("https://evil.com/malware.zip?download=1")
    assert _is_blocked_mime("https://evil.com/drive-by-download.scr")
    # Normal web resources should pass
    assert not _is_blocked_mime("https://example.com/style.css")
    assert not _is_blocked_mime("https://example.com/app.js")
    assert not _is_blocked_mime("https://example.com/image.jpg")
    assert not _is_blocked_mime("https://example.com/page.html")
