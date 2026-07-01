from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalContainsFragment(Rule):
    id = "canonical_contains_fragment"
    name = "Canonical Contains Fragment"
    category = "Canonicals"
    severity = "warning"
    description = "El canonical incluye un fragmento (#...), que Google ignora."
    fix_guidance = (
        "Elimina el fragmento (#...) del canonical. Google ignora los "
        "fragmentos al canonicalizar; usa siempre la URL sin '#'."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, canonical
            FROM urls
            WHERE canonical IS NOT NULL
              AND canonical LIKE '%#%'
            """
        ).fetchall()
        for url_id, url, canonical in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "canonical": canonical},
                message=f"Canonical con fragmento: {canonical}",
            )
