from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MissingHstsHeader(Rule):
    id = "missing_hsts_header"
    name = "Missing HSTS Header"
    category = "Security"
    severity = "info"
    description = (
        "Respuesta HTTPS sin header `Strict-Transport-Security` (HSTS). "
        "El navegador no impondrÃ¡ HTTPS en visitas futuras."
    )
    fix_guidance = (
        "Configura el header `Strict-Transport-Security: max-age=31536000; "
        "includeSubDomains; preload` en todas las respuestas HTTPS."
    )
    references = [
        "https://developer.mozilla.org/docs/Web/HTTP/Headers/Strict-Transport-Security",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE url LIKE 'https://%'
              AND header_hsts IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"Falta header HSTS en respuesta HTTPS: {url}",
            )
