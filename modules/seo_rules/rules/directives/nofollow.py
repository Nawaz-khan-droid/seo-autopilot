from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Nofollow(Rule):
    id = "nofollow"
    name = "Nofollow"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `nofollow` (vÃ­a meta robots o X-Robots-Tag), por lo que "
        "los buscadores no seguirÃ¡n los enlaces salientes desde esta pÃ¡gina."
    )
    fix_guidance = (
        "Si la pÃ¡gina enlaza a contenido propio que quieres rastrear, elimina "
        "`nofollow`. Solo aplÃ­calo a pÃ¡ginas con muchos enlaces externos no "
        "garantizados (UGC, foros, etc.)."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE (LOWER(COALESCE(meta_robots, '')) LIKE '%nofollow%'
                OR LOWER(COALESCE(x_robots_tag, '')) LIKE '%nofollow%')
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
                message=f"URL con nofollow: {url}",
            )
