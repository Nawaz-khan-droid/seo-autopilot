from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class IsolatedViaRedirect(Rule):
    id = "isolated_via_redirect"
    name = "Isolated URL â€” Only Found via Redirect"
    category = "Orphans"
    severity = "warning"
    description = (
        "URL solo descubierta como destino de un redirect, sin enlaces "
        "internos directos."
    )
    fix_guidance = (
        "Sustituye los enlaces internos que apuntan al origen del redirect "
        "por enlaces directos a esta URL final."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT DISTINCT u.url_id, u.url
            FROM urls u
            LEFT JOIN links l ON l.target_url_id = u.url_id
            JOIN redirects r ON r.to_url = u.url
            WHERE l.target_url_id IS NULL
              AND u.status_code = 200
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"{url} solo es accesible como destino de un redirect",
            )
