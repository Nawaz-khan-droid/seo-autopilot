from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangMultipleEntries(Rule):
    id = "hreflang_multiple_entries"
    name = "Hreflang Multiple Entries Same Language"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Una pÃ¡gina declara varias entradas hreflang con la misma lang "
        "(produce ambigÃ¼edad)."
    )
    fix_guidance = (
        "Cada lang debe declararse una sola vez por pÃ¡gina. Consolida o "
        "elimina las entradas duplicadas."
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
                   COUNT(*) AS n,
                   list(h.href ORDER BY h.href) AS hrefs
            FROM hreflang h
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            GROUP BY h.source_url_id, src.url, h.lang
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        for source_url_id, source_url, lang, n, hrefs in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "lang": lang,
                    "count": n,
                    "hrefs": list(hrefs),
                },
                message=(
                    f"{source_url} declara {n} hreflang con lang={lang!r}"
                ),
            )
