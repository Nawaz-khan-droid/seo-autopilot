from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class H2Duplicate(Rule):
    id = "h2_duplicate"
    name = "H2 Duplicate"
    category = "Headings"
    severity = "info"
    description = (
        "Mismo texto de <h2> aparece en mÃºltiples URLs indexables."
    )
    fix_guidance = (
        "Diferencia los <h2> entre pÃ¡ginas para reflejar su contenido Ãºnico. "
        "Encabezados repetidos sugieren plantillas con poco contenido editorial."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            WITH expanded AS (
                SELECT url_id, url, trim(h2_text) AS h
                FROM urls,
                     LATERAL unnest(h2) AS t(h2_text)
                WHERE status_code = 200
                  AND is_indexable = TRUE
                  AND h2 IS NOT NULL
                  AND len(h2) > 0
                  AND h2_text IS NOT NULL
                  AND trim(h2_text) <> ''
            ),
            dups AS (
                SELECT h, COUNT(DISTINCT url_id) AS n,
                       list(DISTINCT url_id) AS url_ids,
                       list(DISTINCT url) AS urls
                FROM expanded
                GROUP BY h
                HAVING COUNT(DISTINCT url_id) > 1
            )
            SELECT h, n, url_ids, urls FROM dups
            """
        ).fetchall()
        for h2_text, n, url_ids, urls in rows:
            for uid, u in zip(url_ids, urls):
                yield Issue(
                    rule_id=self.id,
                    url_id=uid,
                    severity=self.severity,
                    category=self.category,
                    evidence={
                        "h2": h2_text,
                        "duplicate_count": n,
                        "shared_with": [x for x in urls if x != u],
                    },
                    message=f"H2 {h2_text!r} duplicado en {n} URLs",
                )
