from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class BrokenInternalUrl(Rule):
    id = "broken_internal_url"
    name = "Broken internal URLs"
    category = "Response Codes"
    severity = "critical"
    description = (
        "URL interna no funcional: status 0/4XX/5XX y marcada como no indexable."
    )
    fix_guidance = (
        "URLs rotas y no indexables son crawl budget desperdiciado. Encuentra los enlaces "
        "internos que apuntan a ellas y actualÃ­zalos al destino correcto, o configura un 301."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, status_code
            FROM urls
            WHERE (
                    status_code = 0
                    OR status_code IS NULL
                    OR status_code BETWEEN 400 AND 599
                  )
              AND COALESCE(is_indexable, FALSE) = FALSE
            """
        ).fetchall()
        for url_id, url, status in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "status_code": status},
                message=f"URL interna rota y no indexable: {url} ({status})",
            )
