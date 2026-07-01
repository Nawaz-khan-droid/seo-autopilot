from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangNoindexReturn(Rule):
    id = "hreflang_noindex_return"
    name = "Hreflang Noindex Return"
    category = "Hreflang"
    severity = "critical"
    description = (
        "Una declaraciÃ³n hreflang apunta a una URL marcada como noindex "
        "(is_indexable = FALSE)."
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
                   tgt.is_indexable,
                   tgt.indexability_reason
            FROM hreflang h
            JOIN urls tgt ON tgt.url_id = h.href_url_id
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href_url_id IS NOT NULL
              AND tgt.status_code = 200
              AND tgt.is_indexable = FALSE
            """
        ).fetchall()
        for source_url_id, source_url, lang, href, is_indexable, reason in rows:
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
                    f"Hreflang lang={lang!r} en {source_url} apunta a "
                    f"{href}, que no es indexable ({reason})"
                ),
            )
