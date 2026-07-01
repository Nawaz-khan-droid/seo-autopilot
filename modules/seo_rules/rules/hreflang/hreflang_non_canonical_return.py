from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangNonCanonicalReturn(Rule):
    id = "hreflang_non_canonical_return"
    name = "Hreflang Non-Canonical Return"
    category = "Hreflang"
    severity = "warning"
    description = (
        "El hreflang apunta a una URL que estÃ¡ canonicalizada hacia otra "
        "(canonical apunta a una URL distinta de sÃ­ misma)."
    )
    fix_guidance = (
        "El hreflang debe apuntar siempre a la URL canÃ³nica. Actualiza el "
        "href del hreflang para que coincida con la versiÃ³n canÃ³nica."
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
                   tgt.url AS target_url,
                   tgt.canonical
            FROM hreflang h
            JOIN urls tgt ON tgt.url_id = h.href_url_id
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href_url_id IS NOT NULL
              AND tgt.canonical IS NOT NULL
              AND tgt.canonical <> tgt.url
            """
        ).fetchall()
        for source_url_id, source_url, lang, href, target_url, canonical in rows:
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
                    f"Hreflang lang={lang!r} en {source_url} apunta a "
                    f"{target_url}, que estÃ¡ canonicalizada a {canonical}"
                ),
            )
