from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MissingReferrerPolicy(Rule):
    id = "missing_referrer_policy"
    name = "Missing Referrer-Policy"
    category = "Security"
    severity = "info"
    description = (
        "Respuesta sin header `Referrer-Policy`. Por defecto, los navegadores "
        "envÃ­an el referrer completo a otros orÃ­genes."
    )
    fix_guidance = (
        "Configura `Referrer-Policy: strict-origin-when-cross-origin` (o "
        "`no-referrer` si la pÃ¡gina no necesita filtrar trÃ¡fico)."
    )
    references = [
        "https://developer.mozilla.org/docs/Web/HTTP/Headers/Referrer-Policy",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE header_referrer_policy IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"Falta header Referrer-Policy: {url}",
            )
