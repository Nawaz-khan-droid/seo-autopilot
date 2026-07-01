from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlContainsSpace(Rule):
    id = "url_contains_space"
    name = "Contains A Space"
    category = "URL"
    severity = "warning"
    description = "URL contiene un espacio (literal o codificado como %20)."
    fix_guidance = (
        "Evita espacios en URLs. Usa guiones (`-`) entre palabras y "
        "configura redirects 301 desde la versiÃ³n con espacios."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE url LIKE '% %' OR url LIKE '%\\%20%' ESCAPE '\\'
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL contiene espacio: {url}",
            )
