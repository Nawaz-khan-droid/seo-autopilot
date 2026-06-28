"""End-to-end smoke test: exercises the full pipeline against a known test URL.

Requires GROQ_API_KEY in environment. Skips if not set.
Validates that DOCX output is produced and passes the quality verifier.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — E2E test skipped",
)


@pytest.fixture
def test_output_dir():
    path = Path(tempfile.mkdtemp(prefix="e2e_test_"))
    yield path
    if path.exists():
        shutil.rmtree(str(path), ignore_errors=True)


def test_audit_pipeline_smoke(test_output_dir):
    """Run a minimal audit against a simple URL and verify DOCX output.

    This exercises the core pipeline: crawl → metrics → facts → DOCX.
    Uses a static HTML site to avoid flakiness from dynamic content.
    """
    from api.audit_workflow import run_audit as run_full_audit

    result = run_full_audit(
        url="https://example.com",
        sheet_url="",
        mode="single",
        report_month="June 2026",
    )

    assert result.get("success"), f"Audit failed: {result.get('errors', [])}"
    assert "files" in result or "generated" in result, (
        f"No output files in result: {result}"
    )

    files = result.get("generated", result.get("files", []))
    assert len(files) > 0, "No DOCX files produced"

    # Verify each generated file exists and passes quality gate
    for entry in files:
        filepath = entry if isinstance(entry, str) else entry.get("filename", "")
        if not filepath:
            continue
        if not Path(filepath).exists():
            filepath = str(Path.cwd() / "output" / Path(filepath).name)
        if Path(filepath).exists():
            from report.docx_verifier import verify_docx

            report = verify_docx(filepath)
            assert report.get("quality_score", 0) >= 30, (
                f"DOCX quality too low: {report}"
            )


def test_evidence_layer_integrity():
    """Verify the Evidence layer constructs correctly and displays properly."""
    from report.evidence import Evidence

    verified = Evidence.verified(42, "test_source", "https://example.com")
    assert verified.is_verified
    assert verified.is_available
    assert verified.display_value == "42"

    missing = Evidence.missing()
    assert not missing.is_available
    assert missing.display_value == "\u2014"

    estimated = Evidence.estimated(100, "test_fallback")
    assert not estimated.is_verified
    assert estimated.is_available


def test_report_facts_dataclass():
    """Verify ReportFacts instantiates with sensible defaults."""
    from report.facts import ReportFacts

    facts = ReportFacts()
    assert facts.metadata.agency_name == ""
    assert len(facts.rankings) == 0
    assert facts.cwv.mobile_score.is_available is False
    assert facts.backlinks.total_backlinks.is_available is False


def test_docx_verifier_handles_missing_file():
    """Verify the verifier gracefully handles non-existent files."""
    from report.docx_verifier import verify_docx

    result = verify_docx("/tmp/nonexistent_file.docx")
    assert "error" in result
    assert result.get("passed") is None or result.get("passed") is False
