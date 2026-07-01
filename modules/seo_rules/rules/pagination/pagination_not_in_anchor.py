"""TODO(schema): requires extraction of <link rel="next"> / <link rel="prev">
tags. The current schema does not persist these â€” links table only contains
href/anchor data, not rel=next/prev metadata."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class PaginationNotInAnchor(Rule):
    id = "pagination_not_in_anchor"
    name = "Pagination Not In Anchor Tag"
    category = "Pagination"
    severity = "warning"
    description = (
        "URL paginada declarada vÃ­a rel=next/prev pero no enlazada con "
        "un <a href> real."
    )
    fix_guidance = (
        "Enlaza las pÃ¡ginas paginadas con anchors <a href> visibles, "
        "no solo vÃ­a rel=next/prev. Google ya no usa rel=next/prev "
        "como seÃ±al: los enlaces normales son indispensables."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading",
    ]
    # TODO(schema): needs pagination_links table or rel=next/prev metadata.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
