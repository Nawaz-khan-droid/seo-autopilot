from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MetaDescMissing(Rule):
    id = "meta_desc_missing"
    name = "Meta Description Missing"
    category = "Meta Description"
    severity = "warning"
    description = "PÃ¡gina HTML 200 sin <meta name=\"description\">."
    fix_guidance = (
        "AÃ±ade un <meta name=\"description\"> Ãºnico y descriptivo de 70-155 "
        "caracteres que resuma el contenido de la pÃ¡gina y atraiga el clic en SERPs."
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
              AND meta_description IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"PÃ¡gina sin meta description: {url}",
            )
