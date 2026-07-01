from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class H2Missing(Rule):
    id = "h2_missing"
    name = "H2 Missing"
    category = "Headings"
    severity = "info"
    description = "PÃ¡gina indexable sin ningÃºn <h2>."
    fix_guidance = (
        "Estructura el contenido en secciones con <h2> para mejorar legibilidad y "
        "ayudar a buscadores a entender la organizaciÃ³n del contenido."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE status_code = 200
              AND COALESCE(content_type, '') LIKE 'text/html%'
              AND is_indexable = TRUE
              AND (
                    h2 IS NULL
                 OR len(h2) = 0
                 OR len(list_filter(h2, x -> x IS NOT NULL AND trim(x) <> '')) = 0
              )
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"PÃ¡gina sin <h2>: {url}",
            )
