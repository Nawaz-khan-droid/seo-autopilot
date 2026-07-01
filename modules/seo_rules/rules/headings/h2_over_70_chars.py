from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_CHARS = 70


@register_rule
class H2Over70Chars(Rule):
    id = "h2_over_70_chars"
    name = "H2 Over 70 Characters"
    category = "Headings"
    severity = "info"
    description = (
        f"AlgÃºn <h2> de la pÃ¡gina supera los {THRESHOLD_CHARS} caracteres."
    )
    fix_guidance = (
        f"Acorta los <h2> a {THRESHOLD_CHARS} caracteres o menos para mejorar "
        f"la legibilidad y escaneo del contenido."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, h2, max_h2_len FROM (
                SELECT
                    url_id,
                    url,
                    h2,
                    list_max(list_transform(h2, x -> length(x))) AS max_h2_len
                FROM urls
                WHERE status_code = 200
                  AND h2 IS NOT NULL
                  AND len(h2) > 0
            )
            WHERE max_h2_len > ?
            """,
            [THRESHOLD_CHARS],
        ).fetchall()
        for url_id, url, h2, max_len in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "h2": list(h2) if h2 else [],
                    "max_length": max_len,
                    "threshold": THRESHOLD_CHARS,
                },
                message=f"H2 de {max_len} caracteres (>{THRESHOLD_CHARS}): {url}",
            )
