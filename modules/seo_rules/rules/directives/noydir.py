from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Noydir(Rule):
    id = "noydir"
    name = "Noydir"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `noydir`: directiva legacy del antiguo Yahoo Directory. "
        "Hoy no tiene efecto."
    )
    fix_guidance = (
        "Elimina `noydir`: el Yahoo Directory cerrÃ³ en 2014 y los buscadores "
        "actuales ignoran la directiva."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE LOWER(COALESCE(meta_robots, '')) LIKE '%noydir%'
               OR LOWER(COALESCE(x_robots_tag, '')) LIKE '%noydir%'
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
                message=f"URL con directiva legacy noydir: {url}",
            )
