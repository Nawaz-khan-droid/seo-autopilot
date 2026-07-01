from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalNoResponse(Rule):
    id = "internal_no_response"
    name = "Internal No Response"
    category = "Response Codes"
    severity = "critical"
    description = "URL interna que no devuelve respuesta HTTP durante el crawl (status_code = 0)."
    fix_guidance = (
        "Investiga por quÃ© la URL no responde: timeout del servidor, DNS roto, "
        "firewall bloqueando al crawler, o caÃ­da del backend. Asegura disponibilidad "
        "para que Googlebot pueda crawlearla."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE status_code = 0 OR status_code IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "status_code": 0},
                message=f"URL interna no responde: {url}",
            )
