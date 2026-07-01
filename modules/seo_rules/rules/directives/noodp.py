from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Noodp(Rule):
    id = "noodp"
    name = "Noodp"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `noodp`: directiva legacy que pedÃ­a a buscadores no "
        "usar la descripciÃ³n del Open Directory Project. Hoy no tiene efecto."
    )
    fix_guidance = (
        "Elimina `noodp`: el Open Directory Project se cerrÃ³ en 2017 y la "
        "directiva ya no es interpretada por Google, Bing ni Yahoo."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE LOWER(COALESCE(meta_robots, '')) LIKE '%noodp%'
               OR LOWER(COALESCE(x_robots_tag, '')) LIKE '%noodp%'
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
                message=f"URL con directiva legacy noodp: {url}",
            )
