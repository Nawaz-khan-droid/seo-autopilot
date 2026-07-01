from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Nosnippet(Rule):
    id = "nosnippet"
    name = "Nosnippet"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `nosnippet`: Google no mostrarÃ¡ snippet de texto ni "
        "previsualizaciÃ³n de vÃ­deo en la SERP."
    )
    fix_guidance = (
        "Salvo motivos legales o editoriales, evita `nosnippet`: pierdes "
        "espacio visual en la SERP y la posibilidad de optimizar el snippet."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag#directives",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE LOWER(COALESCE(meta_robots, '')) LIKE '%nosnippet%'
               OR LOWER(COALESCE(x_robots_tag, '')) LIKE '%nosnippet%'
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
                message=f"URL con nosnippet: {url}",
            )
