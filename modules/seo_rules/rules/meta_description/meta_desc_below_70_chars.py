from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_CHARS = 70


@register_rule
class MetaDescBelow70Chars(Rule):
    id = "meta_desc_below_70_chars"
    name = "Meta Description Below 70 Characters"
    category = "Meta Description"
    severity = "info"
    description = (
        f"<meta name=\"description\"> con menos de {THRESHOLD_CHARS} caracteres "
        f"(probablemente subÃ³ptimo)."
    )
    fix_guidance = (
        f"Expande la meta description a al menos {THRESHOLD_CHARS} caracteres con "
        f"contexto adicional (beneficios, intenciÃ³n de bÃºsqueda, llamada a la acciÃ³n)."
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
              AND length(trim(meta_description)) > 0
              AND length(meta_description) < ?
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
                message=f"Meta description de solo {d_len} caracteres (<{THRESHOLD_CHARS}): {url}",
            )
