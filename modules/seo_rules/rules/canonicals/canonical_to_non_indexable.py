from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalToNonIndexable(Rule):
    id = "canonical_to_non_indexable"
    name = "Canonical To Non-Indexable"
    category = "Canonicals"
    severity = "warning"
    description = "El canonical apunta a una URL no indexable."
    fix_guidance = (
        "Apunta el canonical a una URL indexable (200, sin noindex, no "
        "bloqueada por robots, sin redirecciones). Un canonical hacia "
        "no-indexable manda seÃ±ales contradictorias a Google."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT a.url_id, a.url, a.canonical, t.is_indexable, t.indexability_reason
            FROM urls a
            JOIN urls t ON t.url = a.canonical
            WHERE a.canonical IS NOT NULL
              AND a.canonical <> a.url
              AND t.is_indexable = FALSE
            """
        ).fetchall()
        for url_id, url, canonical, _idx, reason in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "canonical": canonical,
                    "target_indexable": False,
                    "target_reason": reason,
                },
                message=f"Canonical apunta a URL no indexable: {canonical}",
            )
