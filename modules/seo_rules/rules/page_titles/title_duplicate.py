from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class TitleDuplicate(Rule):
    id = "title_duplicate"
    name = "Title Duplicate"
    category = "Page Titles"
    severity = "warning"
    description = "MÃºltiples URLs indexables comparten exactamente el mismo <title>."
    fix_guidance = (
        "Diferencia los <title> entre pÃ¡ginas: cada URL indexable debe tener uno Ãºnico. "
        "Para pÃ¡ginas paginadas, considera incluir el nÃºmero de pÃ¡gina."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/title-link",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            WITH dups AS (
                SELECT trim(title) AS t, COUNT(*) AS n,
                       list(url_id ORDER BY url_id) AS url_ids,
                       list(url   ORDER BY url_id) AS urls
                FROM urls
                WHERE status_code = 200
                  AND is_indexable = TRUE
                  AND title IS NOT NULL
                  AND trim(title) <> ''
                GROUP BY trim(title)
                HAVING COUNT(*) > 1
            )
            SELECT t, n, url_ids, urls FROM dups
            """
        ).fetchall()
        for title, n, url_ids, urls in rows:
            for uid, u in zip(url_ids, urls):
                yield Issue(
                    rule_id=self.id,
                    url_id=uid,
                    severity=self.severity,
                    category=self.category,
                    evidence={
                        "title": title,
                        "duplicate_count": n,
                        "shared_with": [x for x in urls if x != u],
                    },
                    message=f"Title duplicado en {n} URLs: {title!r}",
                )
