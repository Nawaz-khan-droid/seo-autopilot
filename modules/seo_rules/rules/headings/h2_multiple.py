from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class H2Multiple(Rule):
    id = "h2_multiple"
    name = "H2 Multiple"
    category = "Headings"
    severity = "info"
    description = "PÃ¡gina con mÃ¡s de un <h2> (informativo, no es un problema en sÃ­)."
    fix_guidance = (
        "Tener varios <h2> es lo esperable en pÃ¡ginas con varias secciones. "
        "Esta regla es solo informativa para inventario."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, len(h2) AS n
            FROM urls
            WHERE status_code = 200
              AND h2 IS NOT NULL
              AND len(h2) > 1
            """
        ).fetchall()
        for url_id, url, n in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "h2_count": n},
                message=f"PÃ¡gina con {n} <h2>: {url}",
            )
