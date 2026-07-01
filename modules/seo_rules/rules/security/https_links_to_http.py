from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HttpsLinksToHttp(Rule):
    id = "https_links_to_http"
    name = "HTTPS link to HTTP"
    category = "Security"
    severity = "warning"
    description = (
        "PÃ¡gina HTTPS que enlaza a URLs HTTP. Aunque no es mixed content, "
        "lleva al usuario a un destino menos seguro."
    )
    fix_guidance = (
        "Reemplaza los enlaces `http://` por `https://` cuando el destino "
        "soporte HTTPS, o elimÃ­nalos si no es posible."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/Security",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id,
                   u.url,
                   list(l.target_url) AS http_targets
            FROM urls u
            JOIN links l ON l.source_url_id = u.url_id
            WHERE u.url LIKE 'https://%'
              AND l.target_url LIKE 'http://%'
            GROUP BY u.url_id, u.url
            """
        ).fetchall()
        for url_id, url, http_targets in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "http_targets": list(http_targets),
                    "count": len(http_targets),
                },
                message=(
                    f"La pÃ¡gina HTTPS {url} contiene "
                    f"{len(http_targets)} link(s) a URLs HTTP."
                ),
            )
