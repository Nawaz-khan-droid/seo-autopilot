from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalNofollowInlinksOnly(Rule):
    id = "internal_nofollow_inlinks_only"
    name = "Internal Nofollow Inlinks Only"
    category = "Links"
    severity = "info"
    description = "URL recibe Ãºnicamente inlinks internos con rel=nofollow."
    fix_guidance = (
        "Si la URL es relevante, asegÃºrate de que reciba al menos un inlink "
        "follow para que reciba equity de PageRank."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            WITH per_target AS (
                SELECT
                    l.target_url_id AS uid,
                    SUM(CASE
                            WHEN l.rel IS NOT NULL
                                 AND lower(l.rel) LIKE '%nofollow%'
                            THEN 1 ELSE 0 END) AS n_nofollow,
                    SUM(CASE
                            WHEN l.rel IS NULL
                                 OR lower(l.rel) NOT LIKE '%nofollow%'
                            THEN 1 ELSE 0 END) AS n_follow,
                    COUNT(*) AS n_total
                FROM links l
                WHERE l.target_url_id IS NOT NULL
                GROUP BY l.target_url_id
            )
            SELECT u.url_id, u.url, p.n_nofollow, p.n_total
            FROM per_target p
            JOIN urls u ON u.url_id = p.uid
            WHERE p.n_follow = 0
              AND p.n_nofollow > 0
            """
        ).fetchall()
        for url_id, url, n_nofollow, n_total in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "nofollow_inlinks": n_nofollow,
                    "total_inlinks": n_total,
                },
                message=f"URL recibe solo inlinks nofollow ({n_nofollow}): {url}",
            )
