from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class H1Duplicate(Rule):
    id = "h1_duplicate"
    name = "H1 Duplicate"
    category = "Headings"
    severity = "info"
    description = (
        "MÃºltiples URLs indexables comparten exactamente el mismo primer <h1>."
    )
    fix_guidance = (
        "Diferencia el <h1> entre pÃ¡ginas indexables: cada URL Ãºnica debe tener un "
        "encabezado principal Ãºnico que refleje su contenido."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            WITH first_h1 AS (
                SELECT url_id, url, trim(h1[1]) AS h
                FROM urls
                WHERE status_code = 200
                  AND is_indexable = TRUE
                  AND h1 IS NOT NULL
                  AND len(h1) > 0
                  AND h1[1] IS NOT NULL
                  AND trim(h1[1]) <> ''
            ),
            dups AS (
                SELECT h, COUNT(*) AS n,
                       list(url_id ORDER BY url_id) AS url_ids,
                       list(url    ORDER BY url_id) AS urls
                FROM first_h1
                GROUP BY h
                HAVING COUNT(*) > 1
            )
            SELECT h, n, url_ids, urls FROM dups
            """
        ).fetchall()
        for h1_text, n, url_ids, urls in rows:
            for uid, u in zip(url_ids, urls):
                yield Issue(
                    rule_id=self.id,
                    url_id=uid,
                    severity=self.severity,
                    category=self.category,
                    evidence={
                        "h1": h1_text,
                        "duplicate_count": n,
                        "shared_with": [x for x in urls if x != u],
                    },
                    message=f"H1 duplicado en {n} URLs: {h1_text!r}",
                )
