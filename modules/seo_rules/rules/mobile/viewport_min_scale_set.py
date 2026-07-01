from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ViewportMinScaleSet(Rule):
    id = "viewport_min_scale_set"
    name = "Viewport Minimum Scale Set"
    category = "Mobile"
    severity = "info"
    description = "Viewport declara 'minimum-scale'."
    fix_guidance = (
        "Suele ser innecesario fijar 'minimum-scale'. QuÃ­talo salvo que tengas "
        "una razÃ³n concreta (UX muy especÃ­fica). Generalmente perjudica zoom-out."
    )
    references = [
        "https://web.dev/articles/responsive-web-design-basics",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, viewport
            FROM urls
            WHERE status_code = 200
              AND COALESCE(content_type, '') LIKE 'text/html%'
              AND viewport IS NOT NULL
              AND lower(viewport) LIKE '%minimum-scale%'
            """
        ).fetchall()
        for url_id, url, viewport in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "viewport": viewport},
                message=f"Viewport con minimum-scale en {url}: {viewport!r}",
            )
