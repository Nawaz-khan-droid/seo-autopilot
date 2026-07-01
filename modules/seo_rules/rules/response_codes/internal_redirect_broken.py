from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalRedirectBroken(Rule):
    id = "internal_redirect_broken"
    name = "URL redirect broken"
    category = "Response Codes"
    severity = "critical"
    description = "RedirecciÃ³n apunta a un destino que devuelve 4XX o 5XX."
    fix_guidance = (
        "El destino de la redirecciÃ³n estÃ¡ roto. Actualiza la regla de redirect para "
        "apuntar a una URL que sÃ­ responda 200, o restaura el contenido del destino."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Para cada redirect, mirar el status_code de la URL destino en la tabla urls.
        rows = con.execute(
            """
            SELECT DISTINCT r.from_url, src.url_id, r.to_url, dst.status_code
            FROM redirects r
            JOIN urls dst ON dst.url = r.to_url
            LEFT JOIN urls src ON src.url = r.from_url
            WHERE dst.status_code BETWEEN 400 AND 599
            """
        ).fetchall()
        for from_url, url_id, to_url, dst_status in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": from_url,
                    "redirects_to": to_url,
                    "destination_status": dst_status,
                },
                message=f"Redirect roto: {from_url} â†’ {to_url} ({dst_status})",
            )
