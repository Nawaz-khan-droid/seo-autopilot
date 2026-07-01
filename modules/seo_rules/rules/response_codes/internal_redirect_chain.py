from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalRedirectChain(Rule):
    id = "internal_redirect_chain"
    name = "Internal Redirect Chain"
    category = "Response Codes"
    severity = "warning"
    description = "Cadena de redirecciones de mÃ¡s de un salto (A â†’ B â†’ C)."
    fix_guidance = (
        "Reduce las cadenas a un Ãºnico salto: actualiza la primera redirecciÃ³n para "
        "apuntar directamente al destino final. Cada salto extra desperdicia crawl budget "
        "y diluye seÃ±ales de PageRank."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Una cadena tiene >1 salto si en una chain_id existe alguna fila con hop > 0
        # (es decir, no es solo el primer salto). Reportamos la URL inicial (hop=0) de
        # cada chain_id que tenga al menos un hop > 0.
        rows = con.execute(
            """
            WITH long_chains AS (
                SELECT chain_id, MAX(hop) AS max_hop
                FROM redirects
                GROUP BY chain_id
                HAVING MAX(hop) > 0
            )
            SELECT DISTINCT r.from_url, u.url_id, r.chain_id, lc.max_hop
            FROM redirects r
            JOIN long_chains lc ON lc.chain_id = r.chain_id
            LEFT JOIN urls u ON u.url = r.from_url
            WHERE r.hop = 0
            """
        ).fetchall()
        for from_url, url_id, chain_id, max_hop in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": from_url,
                    "chain_id": chain_id,
                    "hops": max_hop + 1,
                },
                message=f"Cadena de {max_hop + 1} redirects empezando en: {from_url}",
            )
