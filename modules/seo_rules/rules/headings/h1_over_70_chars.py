from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_CHARS = 70


@register_rule
class H1Over70Chars(Rule):
    id = "h1_over_70_chars"
    name = "H1 Over 70 Characters"
    category = "Headings"
    severity = "info"
    description = (
        f"AlgÃºn <h1> de la pÃ¡gina supera los {THRESHOLD_CHARS} caracteres."
    )
    fix_guidance = (
        f"Acorta el <h1> a {THRESHOLD_CHARS} caracteres o menos para que sea "
        f"escaneable por usuarios y crawlers."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, h1, max_h1_len FROM (
                SELECT
                    url_id,
                    url,
                    h1,
                    list_max(list_transform(h1, x -> length(x))) AS max_h1_len
                FROM urls
                WHERE status_code = 200
                  AND h1 IS NOT NULL
                  AND len(h1) > 0
            )
            WHERE max_h1_len > ?
            """,
            [THRESHOLD_CHARS],
        ).fetchall()
        for url_id, url, h1, max_len in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "h1": list(h1) if h1 else [],
                    "max_length": max_len,
                    "threshold": THRESHOLD_CHARS,
                },
                message=f"H1 de {max_len} caracteres (>{THRESHOLD_CHARS}): {url}",
            )
