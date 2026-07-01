from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalRedirectSelf(Rule):
    id = "internal_redirect_self"
    name = "URL redirects to itself"
    category = "Response Codes"
    severity = "critical"
    description = "URL que redirige a sÃ­ misma (from_url == to_url) â€” caso degenerado de loop."
    fix_guidance = (
        "Una URL nunca debe redirigir a sÃ­ misma. Revisa la regla de redirecciÃ³n "
        "(.htaccess, nginx config, plugin SEO, middleware) y elimÃ­nala. Suele venir de "
        "reglas mal escritas tipo 'forzar trailing slash' aplicadas a URLs que ya lo tienen."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT DISTINCT r.from_url, u.url_id, r.status_code
            FROM redirects r
            LEFT JOIN urls u ON u.url = r.from_url
            WHERE r.from_url = r.to_url
            """
        ).fetchall()
        for from_url, url_id, status in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": from_url, "status_code": status},
                message=f"URL redirige a sÃ­ misma: {from_url}",
            )
