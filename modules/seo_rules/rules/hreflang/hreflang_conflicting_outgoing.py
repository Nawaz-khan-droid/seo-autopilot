from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangConflictingOutgoing(Rule):
    id = "hreflang_conflicting_outgoing"
    name = "Hreflang Conflicting Outgoing"
    category = "Hreflang"
    severity = "critical"
    description = (
        "Una pÃ¡gina declara varias entradas hreflang con la misma lang pero "
        "hrefs distintos."
    )
    fix_guidance = (
        "Resuelve la ambigÃ¼edad: para cada lang debe declararse una sola URL "
        "destino."
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
                   list(DISTINCT h.href ORDER BY h.href) AS hrefs
            FROM hreflang h
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            GROUP BY h.source_url_id, src.url, h.lang
            HAVING COUNT(DISTINCT h.href) > 1
            """
        ).fetchall()
        for source_url_id, source_url, lang, hrefs in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "lang": lang,
                    "conflicting_hrefs": list(hrefs),
                },
                message=(
                    f"{source_url} declara lang={lang!r} con "
                    f"{len(hrefs)} hrefs distintos"
                ),
            )
