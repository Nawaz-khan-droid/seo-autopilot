from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class QuerySortParams(Rule):
    id = "query_sort_params"
    name = "Sort parameters"
    category = "URL"
    severity = "info"
    description = (
        "URL con parÃ¡metros de ordenaciÃ³n (`sort=`, `order=`, `orderby=`, "
        "`direction=`). Genera duplicados cuando se indexan."
    )
    fix_guidance = (
        "Decide una ordenaciÃ³n canÃ³nica y declara canonical desde las "
        "variantes. Bloquea el resto con robots.txt si no aportan valor."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE regexp_matches(url, '[?&](sort|order|orderby|direction)=')
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL con sort: {url}",
            )
