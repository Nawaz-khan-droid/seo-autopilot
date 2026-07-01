from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlHasParameters(Rule):
    id = "url_has_parameters"
    name = "Has Parameters"
    category = "URL"
    severity = "info"
    description = "URL contiene query string (`?...`)."
    fix_guidance = (
        "Para URLs pÃºblicas/indexables prefiere paths limpios. Si la "
        "parametrizaciÃ³n es necesaria, declara una canonical y/o usa los "
        "parÃ¡metros como filtros (no como URLs separadas)."
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
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL con parÃ¡metros: {url}",
            )
