from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

INTERNAL_OUTLINKS_THRESHOLD = 300


@register_rule
class PagesHighInternalOutlinks(Rule):
    id = "pages_high_internal_outlinks"
    name = "Pages With High Internal Outlinks"
    category = "Links"
    severity = "info"
    description = (
        f"PÃ¡ginas con mÃ¡s de {INTERNAL_OUTLINKS_THRESHOLD} enlaces internos "
        "(target_url_id IS NOT NULL)."
    )
    fix_guidance = (
        "Demasiados enlaces internos por pÃ¡gina diluyen el equity y dificultan "
        "la priorizaciÃ³n por parte de los buscadores."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id, u.url, COUNT(*) AS n_internal
            FROM links l
            JOIN urls u ON u.url_id = l.source_url_id
            WHERE l.target_url_id IS NOT NULL
            GROUP BY u.url_id, u.url
            HAVING COUNT(*) > ?
            """,
            [INTERNAL_OUTLINKS_THRESHOLD],
        ).fetchall()
        for url_id, url, n_internal in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "internal_outlinks": n_internal,
                    "threshold": INTERNAL_OUTLINKS_THRESHOLD,
                },
                message=f"PÃ¡gina con {n_internal} outlinks internos (>{INTERNAL_OUTLINKS_THRESHOLD}): {url}",
            )
