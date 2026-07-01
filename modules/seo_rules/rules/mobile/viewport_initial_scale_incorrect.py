import re
from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

# Captures the value after initial-scale=
_INITIAL_SCALE_RE = re.compile(
    r"initial-scale\s*=\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE
)


@register_rule
class ViewportInitialScaleIncorrect(Rule):
    id = "viewport_initial_scale_incorrect"
    name = "Viewport Initial Scale Incorrect"
    category = "Mobile"
    severity = "info"
    description = (
        "Viewport tiene initial-scale presente pero distinto de 1 / 1.0."
    )
    fix_guidance = (
        "Usa 'initial-scale=1' (o 1.0). Otros valores producen un zoom inicial "
        "inesperado y suelen romper la apariencia mobile-friendly."
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
              AND lower(viewport) LIKE '%initial-scale%'
            """
        ).fetchall()
        for url_id, url, viewport in rows:
            m = _INITIAL_SCALE_RE.search(viewport)
            if not m:
                continue
            try:
                value = float(m.group(1))
            except ValueError:
                continue
            if value == 1.0:
                continue
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "viewport": viewport,
                    "initial_scale": value,
                },
                message=(
                    f"initial-scale={value} (deberÃ­a ser 1) en {url}"
                ),
            )
