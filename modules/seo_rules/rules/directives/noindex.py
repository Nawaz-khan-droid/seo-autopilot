from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Noindex(Rule):
    id = "noindex"
    name = "Noindex"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `noindex` (vÃ­a meta robots o X-Robots-Tag), por lo que "
        "no serÃ¡ indexada por buscadores."
    )
    fix_guidance = (
        "Verifica que la directiva `noindex` es intencional. Si la URL deberÃ­a "
        "rankear, elimina `noindex` de `<meta name=\"robots\">` o del header "
        "`X-Robots-Tag`."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE (LOWER(COALESCE(meta_robots, '')) LIKE '%noindex%'
                OR LOWER(COALESCE(x_robots_tag, '')) LIKE '%noindex%')
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
                message=f"URL con noindex: {url}",
            )
