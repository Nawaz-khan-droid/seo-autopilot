from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangXDefaultDual(Rule):
    id = "hreflang_x_default_dual"
    name = "Hreflang x-default Dual Declaration"
    category = "Hreflang"
    severity = "info"
    description = (
        "El href usado para lang='x-default' coincide con el href de otro "
        "hreflang con lang concreto en la misma pÃ¡gina."
    )
    fix_guidance = (
        "EstÃ¡ permitido pero suele indicar redundancia. Verifica si ambas "
        "declaraciones son intencionales (pÃ¡gina por defecto = pÃ¡gina de "
        "idioma X)."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT a.source_url_id,
                   src.url AS source_url,
                   a.href,
                   list(b.lang ORDER BY b.lang) AS dup_langs
            FROM hreflang a
            JOIN hreflang b
              ON b.source_url_id = a.source_url_id
             AND b.href = a.href
             AND b.lang <> 'x-default'
            LEFT JOIN urls src ON src.url_id = a.source_url_id
            WHERE a.lang = 'x-default'
            GROUP BY a.source_url_id, src.url, a.href
            """
        ).fetchall()
        for source_url_id, source_url, href, dup_langs in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "shared_href": href,
                    "also_declared_as": list(dup_langs),
                },
                message=(
                    f"x-default en {source_url} apunta a {href}, tambiÃ©n "
                    f"declarado como {list(dup_langs)}"
                ),
            )
