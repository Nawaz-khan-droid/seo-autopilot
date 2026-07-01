from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalNofollowOutlinks(Rule):
    id = "internal_nofollow_outlinks"
    name = "Internal Nofollow Outlinks"
    category = "Links"
    severity = "info"
    description = "La pÃ¡gina enlaza internamente con rel=nofollow."
    fix_guidance = (
        "Revisa si el nofollow interno es intencional. Para enlaces internos "
        "lo habitual es dejarlos follow para distribuir equity."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT l.source_url_id,
                   l.target_url,
                   l.rel,
                   l.anchor
            FROM links l
            WHERE l.target_url_id IS NOT NULL
              AND l.rel IS NOT NULL
              AND lower(l.rel) LIKE '%nofollow%'
            """
        ).fetchall()
        for source_url_id, target_url, rel, anchor in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "target_url": target_url,
                    "rel": rel,
                    "anchor": anchor,
                },
                message=f"Outlink interno con rel=nofollow: {target_url}",
            )
