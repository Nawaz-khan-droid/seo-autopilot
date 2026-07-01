from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class PagesWithoutInternalOutlinks(Rule):
    id = "pages_without_internal_outlinks"
    name = "Pages Without Internal Outlinks"
    category = "Links"
    severity = "warning"
    description = "PÃ¡gina HTML 200 que no enlaza a ninguna URL del propio sitio."
    fix_guidance = (
        "AÃ±ade enlaces internos hacia pÃ¡ginas relacionadas para mejorar el flow "
        "de equity y la navegabilidad."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id, u.url
            FROM urls u
            WHERE u.status_code = 200
              AND COALESCE(u.content_type, '') LIKE 'text/html%'
              AND NOT EXISTS (
                  SELECT 1 FROM links l
                  WHERE l.source_url_id = u.url_id
                    AND l.target_url_id IS NOT NULL
              )
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"PÃ¡gina sin outlinks internos: {url}",
            )
