from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangToCanonicalized(Rule):
    id = "hreflang_to_canonicalized"
    name = "Hreflang to Canonicalized URL"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Hreflang apunta a una URL cuya canonical es distinta de sÃ­ misma "
        "(URL canonicalizada hacia otra)."
    )
    fix_guidance = (
        "Apunta el hreflang directamente a la URL canÃ³nica destino para "
        "evitar seÃ±ales mixtas."
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
                   tgt.canonical
            FROM hreflang h
            JOIN urls tgt ON tgt.url_id = h.href_url_id
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href_url_id IS NOT NULL
              AND tgt.canonical IS NOT NULL
              AND tgt.canonical <> tgt.url
            """
        ).fetchall()
        for source_url_id, source_url, lang, href, canonical in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "lang": lang,
                    "href": href,
                    "target_canonical": canonical,
                },
                message=(
                    f"Hreflang lang={lang!r} apunta a {href}, canonicalizado "
                    f"hacia {canonical}"
                ),
            )
