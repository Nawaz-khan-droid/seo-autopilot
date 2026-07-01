from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalChain(Rule):
    id = "canonical_chain"
    name = "Canonical Chain"
    category = "Canonicals"
    severity = "warning"
    description = "El canonical apunta a una URL que a su vez canonicaliza a otra."
    fix_guidance = (
        "Acorta la cadena: apunta el canonical directamente a la URL final "
        "que se canonicaliza a sÃ­ misma. Las cadenas de canonicals diluyen "
        "seÃ±ales y pueden provocar que Google ignore la directiva."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # A canonicals to B; B canonicals to C (with C != B). Flag A.
        rows = con.execute(
            """
            SELECT a.url_id, a.url, a.canonical AS first_target, b.canonical AS final_target
            FROM urls a
            JOIN urls b ON b.url = a.canonical
            WHERE a.canonical IS NOT NULL
              AND a.canonical <> a.url
              AND b.canonical IS NOT NULL
              AND b.canonical <> b.url
            """
        ).fetchall()
        for url_id, url, first_target, final_target in rows:
            # Skip canonical loops (handled by canonical_loop rule) when final == url
            if final_target == url:
                continue
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "first_target": first_target,
                    "final_target": final_target,
                },
                message=f"Cadena de canonicals: {url} -> {first_target} -> {final_target}",
            )
