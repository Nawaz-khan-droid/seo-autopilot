from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ContentTitleMetaDup(Rule):
    id = "content_title_meta_dup"
    name = "Content Title And Meta Description Duplicate"
    category = "Content"
    severity = "warning"
    description = "MÃºltiples URLs indexables comparten el mismo (title, meta_description)."
    fix_guidance = (
        "Diferencia tanto el <title> como la <meta name='description'> entre URLs. "
        "Si las pÃ¡ginas son realmente equivalentes, consolÃ­dalas con un canonical."
    )
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            WITH dups AS (
                SELECT trim(title) AS t,
                       trim(meta_description) AS m,
                       COUNT(*) AS n,
                       list(url_id ORDER BY url_id) AS url_ids,
                       list(url   ORDER BY url_id) AS urls
                FROM urls
                WHERE is_indexable = TRUE
                  AND title IS NOT NULL AND trim(title) <> ''
                  AND meta_description IS NOT NULL AND trim(meta_description) <> ''
                GROUP BY trim(title), trim(meta_description)
                HAVING COUNT(*) > 1
            )
            SELECT t, m, n, url_ids, urls FROM dups
            """
        ).fetchall()
        for title, meta, n, url_ids, urls in rows:
            for uid, u in zip(url_ids, urls):
                yield Issue(
                    rule_id=self.id,
                    url_id=uid,
                    severity=self.severity,
                    category=self.category,
                    evidence={
                        "url": u,
                        "title": title,
                        "meta_description": meta,
                        "duplicate_count": n,
                        "shared_with": [x for x in urls if x != u],
                    },
                    message=f"Title + meta description duplicados en {n} URLs: {u}",
                )
