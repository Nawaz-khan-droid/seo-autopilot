from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Internal4xx(Rule):
    id = "internal_4xx"
    name = "Internal Client Error (4XX)"
    category = "Response Codes"
    severity = "critical"
    description = "URL interna devuelve un cÃ³digo de error 4XX (cliente)."
    fix_guidance = (
        "Localiza los enlaces internos que apuntan a esta URL y actualÃ­zalos, "
        "o aÃ±ade una redirecciÃ³n 301 hacia la URL correcta. Si el contenido fue "
        "eliminado deliberadamente, devuelve 410 Gone."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, status_code
            FROM urls
            WHERE status_code BETWEEN 400 AND 499
            """
        ).fetchall()
        for url_id, url, status in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "status_code": status},
                message=f"URL interna {status}: {url}",
            )
