from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_CHARS = 155


@register_rule
class MetaDescOver155Chars(Rule):
    id = "meta_desc_over_155_chars"
    name = "Meta Description Over 155 Characters"
    category = "Meta Description"
    severity = "info"
    description = (
        f"<meta name=\"description\"> con mÃ¡s de {THRESHOLD_CHARS} caracteres "
        f"(Google suele truncar)."
    )
    fix_guidance = (
        f"Acorta la meta description a {THRESHOLD_CHARS} caracteres o menos para "
        f"evitar truncado en resultados de bÃºsqueda."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/snippet",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_description, length(meta_description) AS d_len
            FROM urls
            WHERE status_code = 200
              AND meta_description IS NOT NULL
              AND length(meta_description) > ?
            """,
            [THRESHOLD_CHARS],
        ).fetchall()
        for url_id, url, desc, d_len in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "meta_description": desc,
                    "length": d_len,
                    "threshold": THRESHOLD_CHARS,
                },
                message=f"Meta description de {d_len} caracteres (>{THRESHOLD_CHARS}): {url}",
            )
