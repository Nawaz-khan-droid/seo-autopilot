from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class H1Multiple(Rule):
    id = "h1_multiple"
    name = "H1 Multiple"
    category = "Headings"
    severity = "info"
    description = "La pÃ¡gina declara mÃ¡s de un <h1>."
    fix_guidance = (
        "Conserva un Ãºnico <h1> por pÃ¡gina. Convierte los <h1> adicionales en "
        "<h2> para reflejar la jerarquÃ­a real del contenido."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, len(h1) AS n, h1
            FROM urls
            WHERE status_code = 200
              AND h1 IS NOT NULL
              AND len(h1) > 1
            """
        ).fetchall()
        for url_id, url, n, h1 in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "h1_count": n, "h1": list(h1) if h1 else []},
                message=f"PÃ¡gina con {n} <h1>: {url}",
            )
