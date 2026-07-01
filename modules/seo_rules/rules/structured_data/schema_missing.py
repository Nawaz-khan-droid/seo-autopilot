from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SchemaMissing(Rule):
    id = "schema_missing"
    name = "Structured Data Missing"
    category = "Structured Data"
    severity = "info"
    description = (
        "PÃ¡gina HTML 200 indexable sin structured data declarado."
    )
    fix_guidance = (
        "Considera aÃ±adir JSON-LD con el tipo Schema.org mÃ¡s relevante "
        "(Article, Product, Organization, BreadcrumbList...). Mejora la "
        "elegibilidad para rich results."
    )
    references = [
        "https://schema.org/",
        "https://developers.google.com/search/docs/appearance/structured-data",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id, u.url
            FROM urls u
            LEFT JOIN structured_data s ON s.url_id = u.url_id
            WHERE u.status_code = 200
              AND COALESCE(u.content_type, '') LIKE 'text/html%'
              AND u.is_indexable = TRUE
              AND s.url_id IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"{url} no declara structured data",
            )
