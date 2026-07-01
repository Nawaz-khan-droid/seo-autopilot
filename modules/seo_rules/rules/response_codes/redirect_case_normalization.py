from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class RedirectCaseNormalization(Rule):
    id = "redirect_case_normalization"
    name = "Case normalization redirect"
    category = "Response Codes"
    severity = "info"
    description = (
        "RedirecciÃ³n donde from_url y to_url solo difieren en mayÃºsculas/minÃºsculas."
    )
    fix_guidance = (
        "URLs con casing inconsistente generan redirecciones innecesarias. Asegura que "
        "los enlaces internos siempre usen la forma canÃ³nica (tÃ­picamente lowercase) y "
        "evita generar URLs con mayÃºsculas desde plantillas o CMS."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # from_url y to_url son distintos pero idÃ©nticos al pasarlos a lowercase.
        rows = con.execute(
            """
            SELECT DISTINCT r.from_url, u.url_id, r.to_url
            FROM redirects r
            LEFT JOIN urls u ON u.url = r.from_url
            WHERE r.from_url <> r.to_url
              AND lower(r.from_url) = lower(r.to_url)
            """
        ).fetchall()
        for from_url, url_id, to_url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": from_url, "redirects_to": to_url},
                message=f"Redirect solo por case: {from_url} â†’ {to_url}",
            )
