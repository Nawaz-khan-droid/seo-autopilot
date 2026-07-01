from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class H1Missing(Rule):
    id = "h1_missing"
    name = "H1 Missing"
    category = "Headings"
    severity = "warning"
    description = "PÃ¡gina HTML 200 sin <h1> o con todos los <h1> vacÃ­os."
    fix_guidance = (
        "AÃ±ade un Ãºnico <h1> descriptivo al principio del contenido principal "
        "que refleje la temÃ¡tica de la pÃ¡gina."
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
              AND (
                    h1 IS NULL
                 OR len(h1) = 0
                 OR len(list_filter(h1, x -> x IS NOT NULL AND trim(x) <> '')) = 0
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
                message=f"PÃ¡gina sin <h1>: {url}",
            )
