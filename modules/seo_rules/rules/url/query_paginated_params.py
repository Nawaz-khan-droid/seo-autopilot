from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class QueryPaginatedParams(Rule):
    id = "query_paginated_params"
    name = "Paginated parameters"
    category = "URL"
    severity = "info"
    description = (
        "URL con parÃ¡metros de paginaciÃ³n (`page=`, `p=`, `pg=`, `start=`, "
        "`offset=`)."
    )
    fix_guidance = (
        "Las pÃ¡ginas paginadas deben auto-canonicalizar (no apuntar a la "
        "pÃ¡gina 1). AsegÃºrate de que tienen tÃ­tulos diferenciados y son "
        "alcanzables por links HTML (no JS)."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE regexp_matches(url, '[?&](page|p|pg|start|offset|paged)=')
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL paginada: {url}",
            )
