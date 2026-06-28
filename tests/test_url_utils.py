from __future__ import annotations

from modules.url_utils import canonical_url, exact_url_match


class TestCanonicalUrl:
    def test_removes_scheme_and_www(self):
        assert canonical_url("https://www.example.com/path") == "example.com/path"

    def test_handles_missing_scheme(self):
        assert canonical_url("example.com/path") == "example.com/path"

    def test_strips_trailing_slash(self):
        assert canonical_url("https://example.com/path/") == "example.com/path"

    def test_lowercases_hostname(self):
        assert canonical_url("HTTPS://WWW.EXAMPLE.COM/Path") == "example.com/path"

    def test_returns_empty_for_homepage_keyword(self):
        assert canonical_url("homepage") == ""
        assert canonical_url("Home") == ""

    def test_returns_empty_for_relative_path(self):
        assert canonical_url("/relative/path") == ""

    def test_returns_empty_for_none(self):
        assert canonical_url("") == ""
        assert canonical_url(None) == ""  # type: ignore[arg-type]


class TestExactUrlMatch:
    def test_exact_match(self):
        assert exact_url_match(
            "https://www.example.com/page",
            "https://example.com/page",
        )

    def test_no_match_different_domain(self):
        assert not exact_url_match(
            "https://example.com/page",
            "https://other.com/page",
        )

    def test_no_match_different_path(self):
        assert not exact_url_match(
            "https://example.com/page-a",
            "https://example.com/page-b",
        )

    def test_trailing_slash_insensitive(self):
        assert exact_url_match(
            "https://example.com/page/",
            "https://example.com/page",
        )

    def test_empty_url_does_not_match(self):
        assert not exact_url_match("", "https://example.com/page")
