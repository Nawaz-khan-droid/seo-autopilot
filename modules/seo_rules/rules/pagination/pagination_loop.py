"""TODO(schema): requires rel=next/prev metadata to walk paginated sequences
and detect cycles."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class PaginationLoop(Rule):
    id = "pagination_loop"
    name = "Pagination Loop"
    category = "Pagination"
    severity = "warning"
    description = "Secuencia paginada circular (page N -> ... -> page N)."
    fix_guidance = (
        "Rompe el ciclo en la cadena de rel=next/prev. La Ãºltima pÃ¡gina "
        "no debe enlazar de vuelta a la primera mediante rel=next."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading",
    ]
    # TODO(schema): needs pagination_links table.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
