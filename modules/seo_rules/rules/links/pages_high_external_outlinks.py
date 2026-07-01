from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

EXTERNAL_OUTLINKS_THRESHOLD = 100


@register_rule
class PagesHighExternalOutlinks(Rule):
    id = "pages_high_external_outlinks"
    name = "Pages With High External Outlinks"
    category = "Links"
    severity = "info"
    description = (
        f"PÃ¡ginas con mÃ¡s de {EXTERNAL_OUTLINKS_THRESHOLD} enlaces externos "
        "(target_url_id IS NULL)."
    )
    fix_guidance = (
        "Revisa si todos los enlaces externos son necesarios. "
        "Una densidad excesiva puede diluir la temÃ¡tica de la pÃ¡gina."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id, u.url, COUNT(*) AS n_external
            FROM links l
            JOIN urls u ON u.url_id = l.source_url_id
            WHERE l.target_url_id IS NULL
              AND l.target_url IS NOT NULL
              AND (l.target_url LIKE 'http://%' OR l.target_url LIKE 'https://%')
            GROUP BY u.url_id, u.url
            HAVING COUNT(*) > ?
            """,
            [EXTERNAL_OUTLINKS_THRESHOLD],
        ).fetchall()
        for url_id, url, n_external in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "external_outlinks": n_external,
                    "threshold": EXTERNAL_OUTLINKS_THRESHOLD,
                },
                message=f"PÃ¡gina con {n_external} outlinks externos (>{EXTERNAL_OUTLINKS_THRESHOLD}): {url}",
            )
