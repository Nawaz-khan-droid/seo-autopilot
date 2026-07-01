import re
from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

# Match width=NNN or width=NNNpx (specific pixel width, not device-width)
_WIDTH_PX_RE = re.compile(r"width\s*=\s*\d+(?:px)?\b", re.IGNORECASE)


@register_rule
class ViewportSpecificWidth(Rule):
    id = "viewport_specific_width"
    name = "Viewport With Specific Width"
    category = "Mobile"
    severity = "info"
    description = (
        "Viewport declara un ancho fijo en pÃ­xeles (no responsive). "
        "Recomendado usar 'width=device-width'."
    )
    fix_guidance = (
        "Sustituye 'width=320' o similar por 'width=device-width'. "
        "Valores fijos rompen el diseÃ±o responsive en pantallas distintas."
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
              AND lower(viewport) LIKE '%width%'
            """
        ).fetchall()
        for url_id, url, viewport in rows:
            if not _WIDTH_PX_RE.search(viewport):
                continue
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "viewport": viewport},
                message=f"Viewport con ancho fijo en {url}: {viewport!r}",
            )
