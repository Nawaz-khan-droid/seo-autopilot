from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalTo3xx(Rule):
    id = "canonical_to_3xx"
    name = "Canonical Points To Redirect"
    category = "Canonicals"
    severity = "warning"
    description = "El canonical apunta a una URL que redirige (3XX o redirect_count > 0)."
    fix_guidance = (
        "Actualiza el canonical para que apunte directamente a la URL final "
        "(la que devuelve 200), evitando saltos intermedios. Los canonicals "
        "a redirecciones diluyen las seÃ±ales y consumen crawl budget."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT a.url_id, a.url, a.canonical, t.status_code, t.redirect_count
            FROM urls a
            JOIN urls t ON t.url = a.canonical
            WHERE a.canonical IS NOT NULL
              AND a.canonical <> a.url
              AND (
                  (t.status_code BETWEEN 300 AND 399)
                  OR (t.redirect_count IS NOT NULL AND t.redirect_count > 0)
              )
            """
        ).fetchall()
        for url_id, url, canonical, status, hops in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "canonical": canonical,
                    "target_status": status,
                    "redirect_count": hops,
                },
                message=f"Canonical apunta a redirecciÃ³n ({status}): {canonical}",
            )
