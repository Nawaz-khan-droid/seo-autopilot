from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NonIndexablePageInlinksOnly(Rule):
    id = "non_indexable_page_inlinks_only"
    name = "Non-Indexable Page With Inlinks"
    category = "Links"
    severity = "info"
    description = "PÃ¡gina no indexable que recibe enlaces internos."
    fix_guidance = (
        "Si la pÃ¡gina debe quedar fuera del Ã­ndice, considera no enlazarla "
        "internamente para no desperdiciar crawl budget ni equity."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id, u.url, COUNT(l.source_url_id) AS inlinks
            FROM urls u
            JOIN links l ON l.target_url_id = u.url_id
            WHERE u.is_indexable = FALSE
            GROUP BY u.url_id, u.url
            """
        ).fetchall()
        for url_id, url, inlinks in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "inlinks": inlinks},
                message=f"URL no indexable con {inlinks} inlinks: {url}",
            )
