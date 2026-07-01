from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MissingCspHeader(Rule):
    id = "missing_csp_header"
    name = "Missing CSP Header"
    category = "Security"
    severity = "info"
    description = (
        "Respuesta sin header `Content-Security-Policy`. CSP mitiga XSS y "
        "data injection."
    )
    fix_guidance = (
        "Define un Content-Security-Policy ajustado a los orÃ­genes que tu "
        "sitio realmente usa. Empieza en modo `Content-Security-Policy-Report-Only` "
        "para detectar violaciones antes de aplicarlo."
    )
    references = [
        "https://developer.mozilla.org/docs/Web/HTTP/Headers/Content-Security-Policy",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE header_csp IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"Falta header Content-Security-Policy: {url}",
            )
