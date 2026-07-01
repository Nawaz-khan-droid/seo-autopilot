from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NoindexNofollowCombined(Rule):
    id = "noindex_nofollow_combined"
    name = "Noindex Nofollow Combined"
    category = "Directives"
    severity = "warning"
    description = (
        "URL combina `noindex` y `nofollow` en la misma declaraciÃ³n: "
        "no indexa la pÃ¡gina y ademÃ¡s bloquea el traspaso de equity."
    )
    fix_guidance = (
        "Salvo que sea intencional (login, admin, etc.), considera mantener "
        "`noindex, follow` para que el crawler siga descubriendo enlaces "
        "internos desde la pÃ¡gina."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE (
                LOWER(COALESCE(meta_robots, '')) LIKE '%noindex%'
                AND LOWER(COALESCE(meta_robots, '')) LIKE '%nofollow%'
            )
            OR (
                LOWER(COALESCE(x_robots_tag, '')) LIKE '%noindex%'
                AND LOWER(COALESCE(x_robots_tag, '')) LIKE '%nofollow%'
            )
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
                message=f"URL con noindex+nofollow combinados: {url}",
            )
