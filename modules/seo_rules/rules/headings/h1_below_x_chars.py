from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_CHARS = 20


@register_rule
class H1BelowXChars(Rule):
    id = "h1_below_x_chars"
    name = "H1 Too Short"
    category = "Headings"
    severity = "info"
    description = (
        f"<h1> principal con menos de {THRESHOLD_CHARS} caracteres "
        f"(probablemente subÃ³ptimo)."
    )
    fix_guidance = (
        f"Expande el <h1> con contexto adicional (categorÃ­a, intenciÃ³n de bÃºsqueda) "
        f"hasta superar los {THRESHOLD_CHARS} caracteres."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, h1[1] AS first_h1, length(h1[1]) AS h1_len
            FROM urls
            WHERE status_code = 200
              AND h1 IS NOT NULL
              AND len(h1) > 0
              AND h1[1] IS NOT NULL
              AND length(trim(h1[1])) > 0
              AND length(h1[1]) < ?
            """,
            [THRESHOLD_CHARS],
        ).fetchall()
        for url_id, url, first_h1, h1_len in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "h1": first_h1,
                    "length": h1_len,
                    "threshold": THRESHOLD_CHARS,
                },
                message=f"H1 de solo {h1_len} caracteres (<{THRESHOLD_CHARS}): {url}",
            )
