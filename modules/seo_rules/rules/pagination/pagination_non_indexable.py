from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class PaginationNonIndexable(Rule):
    id = "pagination_non_indexable"
    name = "Pagination Non-Indexable"
    category = "Pagination"
    severity = "warning"
    description = "URL paginada marcada como no indexable (noindex, robots, redirect, etc.)."
    fix_guidance = (
        "Las URLs paginadas (page 2, 3, ...) deberÃ­an ser indexables: "
        "Google las usa para descubrir productos/posts en pÃ¡ginas "
        "profundas. Si las haces noindex, considera al menos dejarlas "
        "follow para no romper el descubrimiento."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            r"""
            SELECT url_id, url, indexability_reason
            FROM urls
            WHERE (
                regexp_matches(url, '[?&]page=[0-9]+')
                OR regexp_matches(url, '[?&]p=[0-9]+')
                OR regexp_matches(url, '/page/[0-9]+/?$')
            )
            AND is_indexable = FALSE
            """
        ).fetchall()
        for url_id, url, reason in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "reason": reason},
                message=f"PaginaciÃ³n no indexable ({reason}): {url}",
            )
