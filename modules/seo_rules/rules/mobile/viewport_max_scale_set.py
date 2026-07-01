from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ViewportMaxScaleSet(Rule):
    id = "viewport_max_scale_set"
    name = "Viewport Maximum Scale Set"
    category = "Mobile"
    severity = "info"
    description = "Viewport declara 'maximum-scale' (limita el zoom del usuario)."
    fix_guidance = (
        "Elimina 'maximum-scale' del viewport: limita la accesibilidad para "
        "usuarios con baja visiÃ³n que dependen del pinch-zoom."
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
              AND lower(viewport) LIKE '%maximum-scale%'
            """
        ).fetchall()
        for url_id, url, viewport in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "viewport": viewport},
                message=f"Viewport con maximum-scale en {url}: {viewport!r}",
            )
