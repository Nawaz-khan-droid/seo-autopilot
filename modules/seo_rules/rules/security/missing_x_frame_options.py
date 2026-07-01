from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MissingXFrameOptions(Rule):
    id = "missing_x_frame_options"
    name = "Missing X-Frame-Options"
    category = "Security"
    severity = "info"
    description = (
        "Respuesta sin header `X-Frame-Options`. La pÃ¡gina puede ser embebida "
        "en un iframe (clickjacking)."
    )
    fix_guidance = (
        "Configura `X-Frame-Options: DENY` (o `SAMEORIGIN` si necesitas embeber "
        "internamente). Alternativa moderna: `Content-Security-Policy: frame-ancestors 'none'`."
    )
    references = [
        "https://developer.mozilla.org/docs/Web/HTTP/Headers/X-Frame-Options",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE header_x_frame_options IS NULL
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"Falta header X-Frame-Options: {url}",
            )
