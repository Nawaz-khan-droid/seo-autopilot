from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ViewportNotSet(Rule):
    id = "viewport_not_set"
    name = "Viewport Meta Tag Not Set"
    category = "Mobile"
    severity = "critical"
    description = "PÃ¡gina HTML 200 sin <meta name='viewport'>."
    fix_guidance = (
        "AÃ±ade <meta name=\"viewport\" content=\"width=device-width, "
        "initial-scale=1\"> al <head>. Sin esto, los navegadores mÃ³viles "
        "renderizan la pÃ¡gina a 980 px y aplican zoom-out â€” Google considera la "
        "pÃ¡gina no mobile-friendly."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Viewport_meta_tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE status_code = 200
              AND COALESCE(content_type, '') LIKE 'text/html%'
              AND viewport IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"Sin meta viewport: {url}",
            )
