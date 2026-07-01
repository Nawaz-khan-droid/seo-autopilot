from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


# Phrases that strongly suggest a "page not found" message even though the
# server returned 200 OK. Lower-cased substring match.
SOFT_404_TITLE_PATTERNS = [
    "404",
    "not found",
    "no encontrado",
    "no encontrada",
    "pÃ¡gina no existe",
    "pagina no existe",
    "page not found",
    "doesn't exist",
    "does not exist",
]


@register_rule
class Soft404(Rule):
    id = "soft_404"
    name = "Soft 404"
    category = "Content"
    severity = "warning"
    description = "URL devuelve 200 OK pero el <title> sugiere que la pÃ¡gina no existe."
    fix_guidance = (
        "Si la pÃ¡gina realmente no existe, devuelve un 404/410 explÃ­cito. "
        "Los soft 404 confunden a Google y desperdician crawl budget."
    )
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Build a SQL OR list of LIKE patterns over lowered title.
        like_clauses = " OR ".join(["lower(title) LIKE ?"] * len(SOFT_404_TITLE_PATTERNS))
        params = [f"%{p}%" for p in SOFT_404_TITLE_PATTERNS]
        rows = con.execute(
            f"""
            SELECT url_id, url, title
            FROM urls
            WHERE status_code = 200
              AND title IS NOT NULL
              AND ({like_clauses})
            """,
            params,
        ).fetchall()
        for url_id, url, title in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "title": title},
                message=f"Soft 404 detectado (200 + title de error): {url}",
            )
