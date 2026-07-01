from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MetaDescEmpty(Rule):
    id = "meta_desc_empty"
    name = "Meta Description Empty"
    category = "Meta Description"
    severity = "warning"
    description = "<meta name=\"description\"> presente pero con contenido vacÃ­o."
    fix_guidance = (
        "Rellena el atributo content del <meta name=\"description\"> con un "
        "resumen Ãºnico de 70-155 caracteres."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/snippet",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE status_code = 200
              AND COALESCE(content_type, '') LIKE 'text/html%'
              AND meta_description IS NOT NULL
              AND trim(meta_description) = ''
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"Meta description vacÃ­a: {url}",
            )
