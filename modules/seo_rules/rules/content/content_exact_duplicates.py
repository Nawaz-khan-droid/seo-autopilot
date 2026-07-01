from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ContentExactDuplicates(Rule):
    id = "content_exact_duplicates"
    name = "Content Exact Duplicates"
    category = "Content"
    severity = "warning"
    description = "MÃºltiples URLs indexables comparten exactamente el mismo content_hash."
    fix_guidance = (
        "Consolida el contenido duplicado: usa canonical hacia la versiÃ³n preferida, "
        "o reescribe el contenido para diferenciarlo entre URLs."
    )
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            WITH dups AS (
                SELECT content_hash AS h,
                       COUNT(*) AS n,
                       list(url_id ORDER BY url_id) AS url_ids,
                       list(url   ORDER BY url_id) AS urls
                FROM urls
                WHERE content_hash IS NOT NULL
                  AND content_hash <> ''
                  AND is_indexable = TRUE
                GROUP BY content_hash
                HAVING COUNT(*) > 1
            )
            SELECT h, n, url_ids, urls FROM dups
            """
        ).fetchall()
        for content_hash, n, url_ids, urls in rows:
            for uid, u in zip(url_ids, urls):
                yield Issue(
                    rule_id=self.id,
                    url_id=uid,
                    severity=self.severity,
                    category=self.category,
                    evidence={
                        "url": u,
                        "content_hash": content_hash,
                        "duplicate_count": n,
                        "shared_with": [x for x in urls if x != u],
                    },
                    message=f"Contenido idÃ©ntico en {n} URLs: {u}",
                )
