from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NoneDirective(Rule):
    id = "none"
    name = "None Directive"
    category = "Directives"
    severity = "critical"
    description = (
        "URL declara `none` (equivalente a `noindex, nofollow`), bloqueando "
        "indexaciÃ³n y traspaso de PageRank por completo."
    )
    fix_guidance = (
        "`none` es raramente lo deseado. Si quieres permitir indexaciÃ³n, "
        "sustitÃºyelo por `index, follow` o elimina la directiva."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Match `none` as a token, not substring of e.g. nonexistent.
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE regexp_matches(LOWER(COALESCE(meta_robots, '')), '(^|[\\s,;])none([\\s,;]|$)')
               OR regexp_matches(LOWER(COALESCE(x_robots_tag, '')), '(^|[\\s,;])none([\\s,;]|$)')
            """
        ).fetchall()
        for url_id, url, meta_robots, x_robots_tag in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "meta_robots": meta_robots,
                    "x_robots_tag": x_robots_tag,
                },
                message=f"URL con directiva `none`: {url}",
            )
