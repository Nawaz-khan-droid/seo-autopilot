from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MixedFollowNofollowInlinks(Rule):
    id = "mixed_follow_nofollow_inlinks"
    name = "Mixed Follow / Nofollow Inlinks"
    category = "Links"
    severity = "info"
    description = "URL recibe a la vez inlinks follow e inlinks nofollow."
    fix_guidance = (
        "Verifica que la mezcla follow/nofollow es intencional. "
        "Lo habitual es ser consistente: o todos follow o todos nofollow."
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
                            THEN 1 ELSE 0 END) AS n_follow
                FROM links l
                WHERE l.target_url_id IS NOT NULL
                GROUP BY l.target_url_id
            )
            SELECT u.url_id, u.url, p.n_follow, p.n_nofollow
            FROM per_target p
            JOIN urls u ON u.url_id = p.uid
            WHERE p.n_follow > 0
              AND p.n_nofollow > 0
            """
        ).fetchall()
        for url_id, url, n_follow, n_nofollow in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "follow_inlinks": n_follow,
                    "nofollow_inlinks": n_nofollow,
                },
                message=(
                    f"URL recibe inlinks mixtos: {n_follow} follow + "
                    f"{n_nofollow} nofollow: {url}"
                ),
            )
