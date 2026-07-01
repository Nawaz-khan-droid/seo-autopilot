from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangNon200(Rule):
    id = "hreflang_non_200"
    name = "Hreflang Points to Non-200"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Una declaraciÃ³n hreflang apunta a una URL cuya respuesta no es 200 OK."
    )
    fix_guidance = (
        "Actualiza el href del hreflang a una URL que devuelva 200 OK, "
        "o elimina la declaraciÃ³n si ese idioma/regiÃ³n ya no existe."
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
                   tgt.status_code
            FROM hreflang h
            JOIN urls tgt ON tgt.url_id = h.href_url_id
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href_url_id IS NOT NULL
              AND tgt.status_code IS NOT NULL
              AND tgt.status_code <> 200
            """
        ).fetchall()
        for source_url_id, source_url, lang, href, status_code in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "lang": lang,
                    "href": href,
                    "status_code": status_code,
                },
                message=(
                    f"Hreflang lang={lang!r} apunta a {href} con status "
                    f"{status_code}"
                ),
            )
