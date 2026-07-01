from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalToNoindex(Rule):
    id = "canonical_to_noindex"
    name = "Canonical Points To Noindex"
    category = "Canonicals"
    severity = "warning"
    description = "El canonical apunta a una URL con directiva noindex."
    fix_guidance = (
        "Es una seÃ±al contradictoria: la pÃ¡gina se considera la versiÃ³n "
        "preferida pero a la vez se le pide a Google que no la indexe. "
        "Elimina el noindex de la URL canÃ³nica o cambia el canonical."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT a.url_id, a.url, a.canonical, t.meta_robots, t.x_robots_tag
            FROM urls a
            JOIN urls t ON t.url = a.canonical
            WHERE a.canonical IS NOT NULL
              AND a.canonical <> a.url
              AND (
                  lower(COALESCE(t.meta_robots, '')) LIKE '%noindex%'
                  OR lower(COALESCE(t.x_robots_tag, '')) LIKE '%noindex%'
              )
            """
        ).fetchall()
        for url_id, url, canonical, meta_robots, x_robots in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "canonical": canonical,
                    "target_meta_robots": meta_robots,
                    "target_x_robots_tag": x_robots,
                },
                message=f"Canonical apunta a noindex: {canonical}",
            )
