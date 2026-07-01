from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class QuerySearchFilterParams(Rule):
    id = "query_search_filter_params"
    name = "Search/filter parameters"
    category = "URL"
    severity = "info"
    description = (
        "URL con parÃ¡metros de filtro/categorÃ­a (`filter*=`, `category*=`, "
        "`tag=`, `type=`)."
    )
    fix_guidance = (
        "Las URLs filtradas multiplican el crawl budget y suelen generar "
        "thin/duplicate content. Decide quÃ© combinaciones son indexables y "
        "bloquea el resto con noindex o robots.txt."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE regexp_matches(url, '[?&](filter[a-z_]*|category[a-z_]*|tag|type)=')
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL con filtro/categorÃ­a: {url}",
            )
