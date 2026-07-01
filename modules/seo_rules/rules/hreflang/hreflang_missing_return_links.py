from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangMissingReturnLinks(Rule):
    id = "hreflang_missing_return_links"
    name = "Hreflang Missing Return Links"
    category = "Hreflang"
    severity = "critical"
    description = (
        "La pÃ¡gina A declara hreflang hacia B pero B no devuelve un return "
        "link vÃ¡lido a A con la misma lang."
    )
    fix_guidance = (
        "Cada anotaciÃ³n hreflang debe ser bidireccional: si A declara B con "
        "lang=X, B debe declarar A con la lang correspondiente. Audita el "
        "cluster y aÃ±ade los return links faltantes."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT a.source_url_id,
                   src.url AS source_url,
                   a.lang,
                   a.href,
                   a.href_url_id
            FROM hreflang a
            LEFT JOIN urls src ON src.url_id = a.source_url_id
            LEFT JOIN hreflang b
              ON b.source_url_id = a.href_url_id
             AND b.href_url_id  = a.source_url_id
            WHERE a.href_url_id IS NOT NULL
              AND a.source_url_id <> a.href_url_id
              AND b.source_url_id IS NULL
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
                    "target": href,
                    "target_url_id": href_url_id,
                },
                message=(
                    f"{source_url} declara hreflang lang={lang!r} hacia {href} "
                    f"pero el destino no devuelve return link"
                ),
            )
