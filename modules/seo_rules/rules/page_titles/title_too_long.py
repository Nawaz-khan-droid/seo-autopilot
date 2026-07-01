from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_CHARS = 60


@register_rule
class TitleTooLong(Rule):
    id = "title_too_long"
    name = "Title Too Long"
    category = "Page Titles"
    severity = "info"
    description = f"<title> con mÃ¡s de {THRESHOLD_CHARS} caracteres (Google trunca en SERPs)."
    fix_guidance = (
        f"Acorta el <title> a {THRESHOLD_CHARS} caracteres o menos para evitar "
        f"truncado en resultados de bÃºsqueda."
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
              AND length(title) > ?
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
                message=f"Title de {title_len} caracteres (>{THRESHOLD_CHARS}): {url}",
            )
