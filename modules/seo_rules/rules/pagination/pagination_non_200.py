"""TODO(schema): requires explicit pagination relationship (rel=next/prev)
to know which URLs belong to a paginated sequence. Without that, a 404 on a
?page= URL might be a coincidence, not a broken pagination link."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class PaginationNon200(Rule):
    id = "pagination_non_200"
    name = "Non-200 Pagination"
    category = "Pagination"
    severity = "warning"
    description = "URL declarada como pÃ¡gina de una secuencia paginada con cÃ³digo no-200."
    fix_guidance = (
        "AsegÃºrate de que todas las pÃ¡ginas de una secuencia paginada "
        "responden 200. Una pÃ¡gina intermedia con 404/500 rompe el "
        "descubrimiento de las siguientes."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading",
    ]
    # TODO(schema): needs pagination_links table.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
