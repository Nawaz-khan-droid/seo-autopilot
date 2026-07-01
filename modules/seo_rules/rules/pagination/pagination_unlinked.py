from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class PaginationUnlinked(Rule):
    id = "pagination_unlinked"
    name = "Unlinked Pagination"
    category = "Pagination"
    severity = "warning"
    description = "URL paginada (?page= u otros patrones) sin enlaces internos entrantes."
    fix_guidance = (
        "AsegÃºrate de que las URLs paginadas reciban enlaces internos "
        "desde la pÃ¡gina anterior/siguiente o desde un Ã­ndice. Una URL "
        "paginada sin inlinks no serÃ¡ descubierta ni recrawleada."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Heuristic: URL contains a typical pagination marker AND has no
        # entry as target in `links`. We treat ?page=, &page=, /page/N,
        # ?p= and &p= as pagination signals.
        rows = con.execute(
            r"""
            SELECT u.url_id, u.url
            FROM urls u
            WHERE (
                regexp_matches(u.url, '[?&]page=[0-9]+')
                OR regexp_matches(u.url, '[?&]p=[0-9]+')
                OR regexp_matches(u.url, '/page/[0-9]+/?$')
            )
            AND NOT EXISTS (
                SELECT 1 FROM links l WHERE l.target_url_id = u.url_id
            )
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL paginada sin inlinks: {url}",
            )
