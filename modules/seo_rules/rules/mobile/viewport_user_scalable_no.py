from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ViewportUserScalableNo(Rule):
    id = "viewport_user_scalable_no"
    name = "Viewport User-Scalable=No"
    category = "Mobile"
    severity = "warning"
    description = (
        "Viewport declara 'user-scalable=no', impidiendo el zoom del usuario."
    )
    fix_guidance = (
        "Quita 'user-scalable=no'. Bloquea el pinch-zoom y rompe accesibilidad "
        "WCAG 1.4.4 (resize text). Es seÃ±al de mala prÃ¡ctica para Google."
    )
    references = [
        "https://dequeuniversity.com/rules/axe/4.0/meta-viewport",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, viewport
            FROM urls
            WHERE status_code = 200
              AND COALESCE(content_type, '') LIKE 'text/html%'
              AND viewport IS NOT NULL
              AND replace(replace(lower(viewport), ' ', ''), '"', '')
                  LIKE '%user-scalable=no%'
            """
        ).fetchall()
        for url_id, url, viewport in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "viewport": viewport},
                message=(
                    f"Viewport bloquea zoom (user-scalable=no) en {url}"
                ),
            )
