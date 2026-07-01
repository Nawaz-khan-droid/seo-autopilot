from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangToNoindex(Rule):
    id = "hreflang_to_noindex"
    name = "Hreflang to Noindex URL"
    category = "Hreflang"
    severity = "critical"
    description = (
        "Hreflang apunta a una URL 200 OK pero no indexable (proxy de noindex)."
    )
    fix_guidance = (
        "Las URLs en cluster hreflang deben ser indexables. Quita el noindex "
        "de la URL destino o elimina la declaraciÃ³n hreflang hacia ella."
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
                   h.href,
                   tgt.indexability_reason
            FROM hreflang h
            JOIN urls tgt ON tgt.url_id = h.href_url_id
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href_url_id IS NOT NULL
              AND tgt.status_code = 200
              AND tgt.is_indexable = FALSE
            """
        ).fetchall()
        for source_url_id, source_url, lang, href, reason in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "lang": lang,
                    "href": href,
                    "indexability_reason": reason,
                },
                message=(
                    f"Hreflang lang={lang!r} apunta a {href}, no indexable "
                    f"({reason})"
                ),
            )
