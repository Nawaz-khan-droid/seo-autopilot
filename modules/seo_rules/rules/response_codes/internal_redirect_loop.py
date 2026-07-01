from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalRedirectLoop(Rule):
    id = "internal_redirect_loop"
    name = "Internal Redirect Loop"
    category = "Response Codes"
    severity = "critical"
    description = "URL interna atrapada en un bucle de redirecciones."
    fix_guidance = (
        "Identifica la cadena de redirects (un nodo redirige a otro que vuelve al primero) "
        "y rÃ³mpela apuntando todas las URLs intermedias directamente al destino final con un "
        "Ãºnico 301. Los loops impiden a Googlebot llegar al contenido."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT DISTINCT r.from_url, u.url_id, r.chain_id
            FROM redirects r
            LEFT JOIN urls u ON u.url = r.from_url
            WHERE r.is_loop = TRUE
            """
        ).fetchall()
        for from_url, url_id, chain_id in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": from_url, "chain_id": chain_id},
                message=f"Redirect loop detectado en: {from_url}",
            )
