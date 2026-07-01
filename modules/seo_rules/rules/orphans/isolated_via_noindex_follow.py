from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class IsolatedViaNoindexFollow(Rule):
    id = "isolated_via_noindex_follow"
    name = "Isolated URL â€” Only Found via Noindex,Follow"
    category = "Orphans"
    severity = "warning"
    description = (
        "URL recibe enlaces SOLO desde pÃ¡ginas marcadas como noindex,follow. "
        "Google eventualmente puede dejar de seguir esos enlaces."
    )
    fix_guidance = (
        "Asegura que la URL recibe enlaces desde pÃ¡ginas indexables. "
        "Recibir links solo desde noindex,follow es frÃ¡gil a largo plazo."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            WITH all_inlinks AS (
                SELECT DISTINCT l.target_url_id, src.is_indexable AS src_indexable,
                       COALESCE(src.meta_robots, '') ILIKE '%noindex%'
                       OR COALESCE(src.x_robots_tag, '') ILIKE '%noindex%' AS src_noindex
                FROM links l
                JOIN urls src ON src.url_id = l.source_url_id
                WHERE l.target_url_id IS NOT NULL
            ),
            target_stats AS (
                SELECT target_url_id,
                       COUNT(*) FILTER (WHERE NOT src_noindex) AS indexable_inlinks,
                       COUNT(*) FILTER (WHERE src_noindex) AS noindex_inlinks
                FROM all_inlinks
                GROUP BY target_url_id
            )
            SELECT u.url_id, u.url, ts.noindex_inlinks
            FROM target_stats ts
            JOIN urls u ON u.url_id = ts.target_url_id
            WHERE ts.indexable_inlinks = 0 AND ts.noindex_inlinks > 0
            """
        ).fetchall()
        for url_id, url, n in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "noindex_inlinks": n},
                message=f"{url} solo recibe inlinks desde pÃ¡ginas noindex (n={n})",
            )
