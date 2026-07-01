from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_CHARS = 30


@register_rule
class TitleTooShort(Rule):
    id = "title_too_short"
    name = "Title Too Short"
    category = "Page Titles"
    severity = "info"
    description = f"<title> con menos de {THRESHOLD_CHARS} caracteres (probablemente subÃ³ptimo)."
    fix_guidance = (
        f"Expande el <title> a al menos {THRESHOLD_CHARS} caracteres con contexto "
        f"adicional (marca, secciÃ³n, intenciÃ³n de bÃºsqueda)."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/title-link",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, title, length(title) AS title_len
            FROM urls
            WHERE status_code = 200
              AND title IS NOT NULL
              AND length(trim(title)) > 0
              AND length(title) < ?
            """,
            [THRESHOLD_CHARS],
        ).fetchall()
        for url_id, url, title, title_len in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "title": title, "length": title_len, "threshold": THRESHOLD_CHARS},
                message=f"Title de solo {title_len} caracteres (<{THRESHOLD_CHARS}): {url}",
            )
