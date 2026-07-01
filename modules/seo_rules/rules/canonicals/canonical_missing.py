from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalMissing(Rule):
    id = "canonical_missing"
    name = "Canonical Missing"
    category = "Canonicals"
    severity = "warning"
    description = "PÃ¡gina HTML 200 sin <link rel=\"canonical\">."
    fix_guidance = (
        "AÃ±ade un <link rel=\"canonical\" href=\"...\"> dentro del <head> "
        "apuntando a la URL preferida (incluso si apunta a sÃ­ misma) "
        "para evitar problemas de contenido duplicado."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE status_code = 200
              AND COALESCE(content_type, '') LIKE 'text/html%'
              AND canonical IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"PÃ¡gina sin canonical: {url}",
            )
