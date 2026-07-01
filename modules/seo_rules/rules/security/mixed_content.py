from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MixedContent(Rule):
    id = "mixed_content"
    name = "Mixed Content"
    category = "Security"
    severity = "critical"
    description = (
        "PÃ¡gina HTTPS que carga recursos vÃ­a HTTP (mixed content). Los navegadores "
        "bloquean estos recursos y muestran advertencias de seguridad."
    )
    fix_guidance = (
        "Sirve TODOS los recursos (scripts, stylesheets, imÃ¡genes, iframes...) "
        "vÃ­a HTTPS. Reemplaza URLs `http://` por `https://` o usa rutas "
        "relativas/protocol-relative."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/Security",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id,
                   u.url,
                   list(r.resource_url) AS http_resources,
                   list(r.resource_type) AS http_types
            FROM urls u
            JOIN resources r ON r.source_url_id = u.url_id
            WHERE u.url LIKE 'https://%'
              AND r.resource_url LIKE 'http://%'
            GROUP BY u.url_id, u.url
            """
        ).fetchall()
        for url_id, url, http_resources, http_types in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "http_resources": list(http_resources),
                    "resource_types": list(http_types),
                    "count": len(http_resources),
                },
                message=(
                    f"Mixed content: la pÃ¡gina HTTPS {url} carga "
                    f"{len(http_resources)} recurso(s) vÃ­a HTTP."
                ),
            )
