from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangToDisallowed(Rule):
    id = "hreflang_to_disallowed"
    name = "Hreflang to Disallowed URL"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Hreflang apunta a una URL bloqueada por robots.txt."
    )
    fix_guidance = (
        "Las URLs en cluster hreflang deben ser rastreables. Permite el "
        "rastreo en robots.txt o elimina la declaraciÃ³n hreflang hacia ella."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT h.source_url_id,
                   src.url AS source_url,
                   h.lang,
                   h.href
            FROM hreflang h
            JOIN urls tgt ON tgt.url_id = h.href_url_id
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href_url_id IS NOT NULL
              AND tgt.from_robots = TRUE
            """
        ).fetchall()
        for source_url_id, source_url, lang, href in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "lang": lang,
                    "href": href,
                },
                message=(
                    f"Hreflang lang={lang!r} apunta a {href}, bloqueado por "
                    f"robots.txt"
                ),
            )
