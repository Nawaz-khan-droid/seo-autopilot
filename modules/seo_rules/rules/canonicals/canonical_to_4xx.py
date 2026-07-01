from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalTo4xx(Rule):
    id = "canonical_to_4xx"
    name = "Canonical Points To 4XX"
    category = "Canonicals"
    severity = "critical"
    description = "El canonical apunta a una URL con cÃ³digo 4XX."
    fix_guidance = (
        "Apunta el canonical a una URL viva (HTTP 200). Un canonical a "
        "404/410 es una seÃ±al rota que impide la indexaciÃ³n correcta."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT a.url_id, a.url, a.canonical, t.status_code
            FROM urls a
            JOIN urls t ON t.url = a.canonical
            WHERE a.canonical IS NOT NULL
              AND a.canonical <> a.url
              AND t.status_code BETWEEN 400 AND 499
            """
        ).fetchall()
        for url_id, url, canonical, status in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "canonical": canonical,
                    "target_status": status,
                },
                message=f"Canonical apunta a {status}: {canonical}",
            )
