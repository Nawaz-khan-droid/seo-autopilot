from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


# Schemes considered "valid web links" that we do NOT want to flag.
_ALLOWED_PREFIXES = ("http://", "https://", "mailto:", "tel:", "sms:", "/", "#", "?")


@register_rule
class LinkNonHttpProtocol(Rule):
    id = "link_non_http_protocol"
    name = "Link Non HTTP Protocol"
    category = "Links"
    severity = "warning"
    description = "Link con protocolo no estÃ¡ndar (ftp://, gopher://, irc://, etc.)."
    fix_guidance = (
        "Sustituye los enlaces con protocolos exÃ³ticos por equivalentes HTTP(S) "
        "o elimÃ­nalos si no aportan valor."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # We pull all links and filter in Python: detecting "scheme:" generically
        # in DuckDB SQL is more error-prone than a small Python predicate.
        rows = con.execute(
            """
            SELECT source_url_id, target_url, anchor
            FROM links
            WHERE target_url IS NOT NULL
              AND target_url <> ''
            """
        ).fetchall()
        for source_url_id, target_url, anchor in rows:
            t = target_url.strip().lower()
            if not t:
                continue
            if any(t.startswith(p) for p in _ALLOWED_PREFIXES):
                continue
            # Detect "scheme:" pattern (letters followed by colon, before slash/?)
            colon = t.find(":")
            if colon <= 0:
                continue
            scheme = t[:colon]
            if not scheme.isalpha():
                continue
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "target_url": target_url,
                    "anchor": anchor,
                    "scheme": scheme,
                },
                message=f"Link con protocolo {scheme}:// detectado: {target_url}",
            )
