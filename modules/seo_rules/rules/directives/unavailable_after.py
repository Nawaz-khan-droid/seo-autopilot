from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UnavailableAfter(Rule):
    id = "unavailable_after"
    name = "Unavailable After"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `unavailable_after`, lo que indica al buscador que la "
        "pÃ¡gina dejarÃ¡ de ser indexable a partir de la fecha indicada."
    )
    fix_guidance = (
        "Verifica que la fecha es correcta. Si la pÃ¡gina debe seguir "
        "indexada de forma indefinida, elimina la directiva."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag#directives",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE LOWER(COALESCE(meta_robots, '')) LIKE '%unavailable_after%'
               OR LOWER(COALESCE(x_robots_tag, '')) LIKE '%unavailable_after%'
            """
        ).fetchall()
        for url_id, url, meta_robots, x_robots_tag in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "meta_robots": meta_robots,
                    "x_robots_tag": x_robots_tag,
                },
                message=f"URL con unavailable_after: {url}",
            )
