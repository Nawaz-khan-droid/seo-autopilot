from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangRelativeUrls(Rule):
    id = "hreflang_relative_urls"
    name = "Hreflang Relative URLs"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Una anotaciÃ³n hreflang usa una URL relativa en lugar de absoluta."
    )
    fix_guidance = (
        "Google recomienda URLs absolutas (con esquema y host completos) en "
        "anotaciones hreflang para evitar ambigÃ¼edad."
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
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href IS NOT NULL
              AND lower(h.href) NOT LIKE 'http://%'
              AND lower(h.href) NOT LIKE 'https://%'
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
                    f"Hreflang lang={lang!r} usa URL relativa: {href!r}"
                ),
            )
