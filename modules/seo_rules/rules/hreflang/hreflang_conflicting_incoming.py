from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangConflictingIncoming(Rule):
    id = "hreflang_conflicting_incoming"
    name = "Hreflang Conflicting Incoming"
    category = "Hreflang"
    severity = "critical"
    description = (
        "Distintas pÃ¡ginas declaran la misma URL destino con la misma lang "
        "(mÃºltiples pÃ¡ginas reclaman ser la misma versiÃ³n idiomÃ¡tica)."
    )
    fix_guidance = (
        "SÃ³lo una URL en el sitio puede ser la versiÃ³n X para una lang dada. "
        "Revisa el cluster y consolida."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT h.lang,
                   h.href,
                   COUNT(DISTINCT h.source_url_id) AS n_sources,
                   list(DISTINCT h.source_url_id ORDER BY h.source_url_id) AS source_ids
            FROM hreflang h
            WHERE h.href_url_id IS NOT NULL
            GROUP BY h.lang, h.href
            HAVING COUNT(DISTINCT h.source_url_id) > 1
            """
        ).fetchall()
        for lang, href, n_sources, source_ids in rows:
            for sid in source_ids:
                yield Issue(
                    rule_id=self.id,
                    url_id=sid,
                    severity=self.severity,
                    category=self.category,
                    evidence={
                        "lang": lang,
                        "shared_href": href,
                        "source_count": n_sources,
                        "source_url_ids": list(source_ids),
                    },
                    message=(
                        f"{n_sources} pÃ¡ginas declaran lang={lang!r} hacia "
                        f"{href}"
                    ),
                )
