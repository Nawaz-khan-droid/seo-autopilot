from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class QueryMoreThanThreeParams(Rule):
    id = "query_more_than_three_params"
    name = "More than 3 query params"
    category = "URL"
    severity = "info"
    description = (
        "URL con mÃ¡s de 3 parÃ¡metros en la query. MÃ¡s parÃ¡metros = mÃ¡s "
        "combinaciones que crawlear y mayor riesgo de duplicaciÃ³n."
    )
    fix_guidance = (
        "Consolida parÃ¡metros donde sea posible y revisa quÃ© combinaciones "
        "son indexables. Considera bloquear las no Ãºtiles en robots.txt o "
        "vÃ­a canonical."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE position('?' IN url) > 0
            """
        ).fetchall()
        for url_id, url in rows:
            qs = url.split("?", 1)[1].split("#", 1)[0]
            params = [p for p in qs.split("&") if p]
            if len(params) <= 3:
                continue
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "param_count": len(params)},
                message=f"URL con {len(params)} parÃ¡metros (> 3): {url}",
            )
