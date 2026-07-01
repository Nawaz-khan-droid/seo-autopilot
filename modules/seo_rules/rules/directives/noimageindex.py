from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Noimageindex(Rule):
    id = "noimageindex"
    name = "Noimageindex"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `noimageindex`: las imÃ¡genes de la pÃ¡gina no se "
        "indexarÃ¡n en Google Images."
    )
    fix_guidance = (
        "Si las imÃ¡genes de la pÃ¡gina deberÃ­an rankear en Google Images, "
        "elimina `noimageindex`."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag#directives",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE LOWER(COALESCE(meta_robots, '')) LIKE '%noimageindex%'
               OR LOWER(COALESCE(x_robots_tag, '')) LIKE '%noimageindex%'
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
                message=f"URL con noimageindex: {url}",
            )
