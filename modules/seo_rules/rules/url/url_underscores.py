from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlUnderscores(Rule):
    id = "url_underscores"
    name = "Underscores"
    category = "URL"
    severity = "info"
    description = (
        "Path de la URL contiene `_`. Google recomienda guiones (`-`) como "
        "separador de palabras en URLs."
    )
    fix_guidance = (
        "Sustituye underscores por guiones. Configura redirects 301 desde la "
        "versiÃ³n antigua con underscores."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Solo en path/query, no en host (algunos hosts internos pueden tener `_`).
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE position('_' IN regexp_replace(url, '^[^/]*//[^/]*', '')) > 0
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL con underscore en path: {url}",
            )
