from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalRedirect3xx(Rule):
    id = "internal_redirect_3xx"
    name = "Internal Redirection (3XX)"
    category = "Response Codes"
    severity = "info"
    description = "URL interna que pasÃ³ por al menos una redirecciÃ³n (redirect_count > 0)."
    fix_guidance = (
        "Revisa los enlaces internos para que apunten directamente a la URL final, "
        "evitando el salto. Las redirecciones son aceptables pero ahorran crawl budget "
        "si los enlaces internos van directos al destino."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, redirect_count, final_url
            FROM urls
            WHERE redirect_count > 0
            """
        ).fetchall()
        for url_id, url, redirect_count, final_url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "redirect_count": redirect_count,
                    "final_url": final_url,
                },
                message=f"URL pasa por {redirect_count} redirect(s): {url}",
            )
