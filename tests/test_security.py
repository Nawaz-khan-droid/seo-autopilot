"""Security penetration tests — validate all vulnerability fixes."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.main import (
    _sanitize_filename_component,
    _validate_url_not_private,
    _RateLimiter,
    _PRIVATE_HOST_PREFIXES,
    _METADATA_HOSTS,
)
from api.crawl_engine import _resolve_and_validate_target, _is_malware_request, _is_blocked_mime
from fastapi import HTTPException


# ── Path traversal protection ──

class TestSanitizeFilenameComponent:
    def test_strips_dotdot(self):
        assert "etcpasswd" == _sanitize_filename_component("../../etc/passwd")

    def test_strips_backslash(self):
        result = _sanitize_filename_component("..\\..\\Windows\\win.ini")
        assert ".." not in result and "\\" not in result and ":" not in result

    def test_strips_colon(self):
        assert "CWindows" == _sanitize_filename_component("C:\\Windows\\")

    def test_whitespace_stripped(self):
        assert "client" == _sanitize_filename_component("  client  ")

    def test_returns_empty_for_all_invalid(self):
        assert "" == _sanitize_filename_component("../../../..")

    def test_normal_name_preserved(self):
        assert "Acme Corp" == _sanitize_filename_component("Acme Corp")


# ── SSRF protection ──

class TestValidateUrlNotPrivate:
    def test_public_url_passes(self):
        _validate_url_not_private("https://www.google.com")

    def test_public_url_with_path_passes(self):
        _validate_url_not_private("https://example.com/page?q=1")

    def test_localhost_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://localhost:8000")

    def test_loopback_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://127.0.0.1:3000")

    def test_wildcard_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://0.0.0.0:8080")

    def test_ipv6_loopback_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://[::1]:8080")

    def test_private_10_dot_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://10.0.0.1:8080")

    def test_private_172_16_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://172.16.0.1:8080")

    def test_private_172_31_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://172.31.255.255")

    def test_private_192_168_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://192.168.1.1:8080")

    def test_link_local_169_254_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://169.254.169.254")

    def test_metadata_host_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://metadata.google.internal")

    def test_metadata_host_aws_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://100.100.100.200")

    def test_metadata_host_gcp_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("http://100.100.100.204")

    def test_empty_host_rejected(self):
        with pytest.raises(HTTPException):
            _validate_url_not_private("not-a-url")

    def test_private_prefixes_complete(self):
        """Verify all 172.x.x.x private ranges are covered."""
        for i in range(16, 32):
            assert f"172.{i}." in _PRIVATE_HOST_PREFIXES, f"172.{i}.0.0/20 not covered"

    def test_metadata_hosts_contains_known(self):
        assert "169.254.169.254" in _METADATA_HOSTS
        assert "metadata.google.internal" in _METADATA_HOSTS


class TestResolveAndValidateTarget:
    """These tests require DNS resolution — only run if network available."""

    def test_public_domain_resolves_safe(self):
        result = _resolve_and_validate_target("https://google.com")
        assert result is True

    def test_private_ip_returns_false(self):
        result = _resolve_and_validate_target("http://127.0.0.1:8080")
        assert result is False

    def test_invalid_url_returns_false(self):
        result = _resolve_and_validate_target("not-a-valid-url-at-all-12345")
        assert result is False

    def test_empty_hostname_returns_false(self):
        result = _resolve_and_validate_target("")
        assert result is False


# ── Malware & MIME blocklist ──

class TestMalwareBlocklist:
    def test_known_malware_domain_blocked(self):
        assert _is_malware_request("http://malware.testing.google.test/evil.exe") is True

    def test_subdomain_of_malware_blocked(self):
        assert _is_malware_request("http://sub.malware.testing.google.test/") is True

    def test_clean_domain_allowed(self):
        assert _is_malware_request("http://google.com/") is False

    def test_blocked_exe_mime(self):
        assert _is_blocked_mime("http://example.com/virus.exe") is True

    def test_blocked_scr_mime(self):
        assert _is_blocked_mime("http://example.com/screen.scr") is True

    def test_normal_html_allowed(self):
        assert _is_blocked_mime("http://example.com/page.html") is False

    def test_normal_php_allowed(self):
        assert _is_blocked_mime("http://example.com/index.php") is False


# ── Rate limiter ──

class TestRateLimiter:
    def test_allows_within_limit(self):
        limiter = _RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.check("1.2.3.4") is True
        assert limiter.check("1.2.3.4") is True
        assert limiter.check("1.2.3.4") is True

    def test_blocks_when_exceeded(self):
        limiter = _RateLimiter(max_requests=3, window_seconds=60)
        limiter.check("1.2.3.5")
        limiter.check("1.2.3.5")
        limiter.check("1.2.3.5")
        assert limiter.check("1.2.3.5") is False

    def test_different_ips_independent(self):
        limiter = _RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.check("10.0.0.1") is True
        assert limiter.check("10.0.0.1") is False
        assert limiter.check("10.0.0.2") is True

    def test_window_expires(self):
        import time
        limiter = _RateLimiter(max_requests=1, window_seconds=0.1)
        assert limiter.check("1.2.3.6") is True
        assert limiter.check("1.2.3.6") is False
        time.sleep(0.15)
        assert limiter.check("1.2.3.6") is True


# ── Gitignore coverage ──

class TestGitignore:
    def test_secrets_credentials_ignored(self):
        gitignore = Path(__file__).resolve().parent.parent / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "secrets/credentials.json" in content, "secrets/credentials.json not in .gitignore"

    def test_root_credentials_ignored(self):
        gitignore = Path(__file__).resolve().parent.parent / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "credentials.json" in content

    def test_env_ignored(self):
        gitignore = Path(__file__).resolve().parent.parent / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert ".env" in content

    def test_cert_files_ignored(self):
        gitignore = Path(__file__).resolve().parent.parent / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "*.pem" in content
        assert "*.key" in content


# ── docker-compose.yml consistency ──

class TestDockerCompose:
    def test_no_dead_worker_service(self):
        """Verify the worker service block (not just the word) is removed."""
        import yaml  # pyyaml is available indirectly
        path = Path(__file__).resolve().parent.parent / "docker-compose.yml"
        with open(str(path), encoding="utf-8") as f:
            parsed = yaml.safe_load(f)
        services = parsed.get("services", {})
        assert "worker" not in services, "dead worker service still present in docker-compose"

    def test_no_opentelemetry_cmd(self):
        path = Path(__file__).resolve().parent.parent / "Dockerfile"
        content = path.read_text(encoding="utf-8")
        assert "opentelemetry-instrument" not in content, "removed OpenTelemetry still referenced"


# ── requirements.txt CVE fixes ──

class TestRequirementsCVE:
    def test_dotenv_pinned_safe(self):
        path = Path(__file__).resolve().parent.parent / "requirements.txt"
        content = path.read_text(encoding="utf-8")
        assert any("python-dotenv>=1.2" in line for line in content.splitlines()), \
            "python-dotenv must be >= 1.2.2 for CVE-2026-28684"

    def test_urllib3_pinned_safe(self):
        path = Path(__file__).resolve().parent.parent / "requirements.txt"
        content = path.read_text(encoding="utf-8")
        assert any("urllib3>=2.7" in line for line in content.splitlines()), \
            "urllib3 must be >= 2.7.0 for multiple CVEs"

    def test_no_cve_vulnerable_pins(self):
        """Verify no pyseoanalyzer version pins override CVE fixes."""
        path = Path(__file__).resolve().parent.parent / "requirements.txt"
        content = path.read_text(encoding="utf-8")
        assert "# pyseoanalyzer>=0.1.0" in content or "pyseoanalyzer" not in content, \
            "pyseoanalyzer's strict pins would reintroduce CVEs"


# ── HTTPS support ──

class TestHttpsSupport:
    def test_ssl_env_vars_wired(self):
        path = Path(__file__).resolve().parent.parent / "api" / "main.py"
        content = path.read_text(encoding="utf-8")
        assert "SSL_CERTFILE" in content
        assert "SSL_KEYFILE" in content


# ── Facts assembler SSRF protection ──

class TestFactsAssemblerSSRF:
    def test_imports_resolve_and_validate(self):
        from api.facts_assembler import _build_facts_from_audit
        import inspect
        source = inspect.getsource(_build_facts_from_audit)
        assert "_resolve_and_validate_target" in source, \
            "facts_assembler must validate targets before HEAD requests"
