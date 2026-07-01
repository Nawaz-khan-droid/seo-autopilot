from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MetaDescDuplicate(Rule):
    id = "meta_desc_duplicate"
    name = "Meta Description Duplicate"
    category = "Meta Description"
    severity = "info"
    description = (
        "MÃºltiples URLs indexables comparten exactamente la misma meta description."
    )
    fix_guidance = (
        "Diferencia la meta description en cada URL indexable: cada pÃ¡gina deberÃ­a "
        "tener un resumen propio que refleje su contenido Ãºnico."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/snippet",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            WITH dups AS (
                SELECT trim(meta_description) AS d, COUNT(*) AS n,
                       list(url_id ORDER BY url_id) AS url_ids,
                       list(url    ORDER BY url_id) AS urls
                FROM urls
                WHERE status_code = 200
                  AND is_indexable = TRUE
                  AND meta_description IS NOT NULL
                  AND trim(meta_description) <> ''
                GROUP BY trim(meta_description)
                HAVING COUNT(*) > 1
            )
            SELECT d, n, url_ids, urls FROM dups
            """
        ).fetchall()
        for desc, n, url_ids, urls in rows:
            for uid, u in zip(url_ids, urls):
                yield Issue(
                    rule_id=self.id,
                    url_id=uid,
                    severity=self.severity,
                    category=self.category,
                    evidence={
                        "meta_description": desc,
                        "duplicate_count": n,
                        "shared_with": [x for x in urls if x != u],
                    },
                    message=f"Meta description duplicada en {n} URLs: {desc!r}",
                )
