from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangUnlinked(Rule):
    id = "hreflang_unlinked"
    name = "Hreflang Unlinked"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Una URL declarada en hreflang no estÃ¡ enlazada internamente desde "
        "ningÃºn sitio del crawl (sÃ³lo descubierta vÃ­a hreflang)."
    )
    fix_guidance = (
        "AÃ±ade enlaces internos hacia las versiones lingÃ¼Ã­sticas para que "
        "Google pueda descubrirlas y rastrearlas con normalidad."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT DISTINCT h.source_url_id,
                            src.url AS source_url,
                            h.lang,
                            h.href,
                            h.href_url_id
            FROM hreflang h
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href_url_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM links l
                  WHERE l.target_url_id = h.href_url_id
              )
            """
        ).fetchall()
        for source_url_id, source_url, lang, href, href_url_id in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "lang": lang,
                    "href": href,
                    "target_url_id": href_url_id,
                },
                message=(
                    f"Hreflang lang={lang!r} apunta a {href}, que no recibe "
                    f"enlaces internos desde ninguna otra pÃ¡gina"
                ),
            )
