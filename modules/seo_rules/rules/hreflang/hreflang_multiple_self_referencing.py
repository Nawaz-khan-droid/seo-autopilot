from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangMultipleSelfReferencing(Rule):
    id = "hreflang_multiple_self_referencing"
    name = "Hreflang Multiple Self References"
    category = "Hreflang"
    severity = "warning"
    description = (
        "La misma pÃ¡gina tiene varias entradas hreflang que se apuntan a sÃ­ "
        "misma (tÃ­picamente con langs distintas)."
    )
    fix_guidance = (
        "Solo debe haber una self-reference por pÃ¡gina, con la lang real de "
        "esa URL. Elimina las entradas redundantes."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT h.source_url_id,
                   src.url AS source_url,
                   COUNT(*) AS n,
                   list(h.lang ORDER BY h.lang) AS langs
            FROM hreflang h
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.source_url_id = h.href_url_id
               OR h.href = src.url
            GROUP BY h.source_url_id, src.url
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        for source_url_id, source_url, n, langs in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "self_ref_count": n,
                    "langs": list(langs),
                },
                message=(
                    f"{source_url} tiene {n} self-references con langs "
                    f"{list(langs)!r}"
                ),
            )
