from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangNoindexHasIncoming(Rule):
    id = "hreflang_noindex_has_incoming"
    name = "Hreflang to Noindex URL (incoming)"
    category = "Hreflang"
    severity = "critical"
    description = (
        "Una URL noindex (status 200 pero no indexable por noindex/header) "
        "recibe hreflang entrantes. El cluster serÃ¡ descartado por Google."
    )
    fix_guidance = (
        "Retira la directiva noindex o redirige los hreflang a una URL "
        "indexable del mismo idioma/regiÃ³n."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT DISTINCT u.url_id, u.url, u.indexability_reason
            FROM urls u
            JOIN hreflang h ON h.href_url_id = u.url_id
            WHERE u.status_code = 200
              AND u.is_indexable = FALSE
              AND (
                  COALESCE(u.meta_robots, '') ILIKE '%noindex%'
                  OR COALESCE(u.x_robots_tag, '') ILIKE '%noindex%'
              )
            """
        ).fetchall()
        for url_id, url, reason in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "reason": reason},
                message=f"{url} es noindex pero recibe hreflang entrantes",
            )
