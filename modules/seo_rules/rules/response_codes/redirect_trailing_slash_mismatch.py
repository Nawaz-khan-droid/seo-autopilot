from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class RedirectTrailingSlashMismatch(Rule):
    id = "redirect_trailing_slash_mismatch"
    name = "Trailing slash mismatch"
    category = "Response Codes"
    severity = "info"
    description = (
        "RedirecciÃ³n donde from_url y to_url solo difieren en la barra final (trailing slash)."
    )
    fix_guidance = (
        "Define una sola convenciÃ³n (con o sin trailing slash) y aplÃ­cala desde el origen "
        "de los enlaces internos. Que los enlaces internos ya apunten a la forma canÃ³nica "
        "evita el redirect intermedio."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Compara from_url y to_url normalizando el trailing slash final.
        # Si tras normalizar son iguales pero originales no lo eran, hay mismatch.
        rows = con.execute(
            """
            SELECT DISTINCT r.from_url, u.url_id, r.to_url
            FROM redirects r
            LEFT JOIN urls u ON u.url = r.from_url
            WHERE r.from_url <> r.to_url
              AND regexp_replace(r.from_url, '/$', '') =
                  regexp_replace(r.to_url,   '/$', '')
            """
        ).fetchall()
        for from_url, url_id, to_url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": from_url, "redirects_to": to_url},
                message=f"Redirect solo por trailing slash: {from_url} â†’ {to_url}",
            )
