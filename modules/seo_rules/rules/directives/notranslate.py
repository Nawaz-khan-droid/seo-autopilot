from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Notranslate(Rule):
    id = "notranslate"
    name = "Notranslate"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `notranslate`: Google no ofrecerÃ¡ traducciÃ³n automÃ¡tica "
        "en la SERP."
    )
    fix_guidance = (
        "Si quieres que usuarios en otros idiomas vean traducciÃ³n automÃ¡tica, "
        "elimina `notranslate`. Es Ãºtil dejarla solo cuando la traducciÃ³n "
        "romperÃ­a tÃ©rminos tÃ©cnicos o legales."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag#directives",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE LOWER(COALESCE(meta_robots, '')) LIKE '%notranslate%'
               OR LOWER(COALESCE(x_robots_tag, '')) LIKE '%notranslate%'
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
                message=f"URL con notranslate: {url}",
            )
