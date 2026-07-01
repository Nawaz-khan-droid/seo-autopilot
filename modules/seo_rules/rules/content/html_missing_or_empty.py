from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HtmlMissingOrEmpty(Rule):
    id = "html_missing_or_empty"
    name = "HTML Missing Or Empty"
    category = "Content"
    severity = "critical"
    description = "Respuesta HTML 200 con cuerpo vacÃ­o (content_length 0 o NULL)."
    fix_guidance = (
        "Verifica que el servidor estÃ¡ devolviendo el HTML correctamente. "
        "Una respuesta 200 con cuerpo vacÃ­o es frecuentemente un fallo de origen "
        "o un mal rewrite."
    )
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, content_length
            FROM urls
            WHERE status_code = 200
              AND COALESCE(content_type, '') LIKE 'text/html%'
              AND (content_length IS NULL OR content_length = 0)
            """
        ).fetchall()
        for url_id, url, clen in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "content_length": clen},
                message=f"HTML vacÃ­o o ausente en respuesta 200: {url}",
            )
