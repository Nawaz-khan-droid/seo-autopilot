"""TODO(schema): requires rel=next/prev metadata to verify ordering."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class PaginationSequenceError(Rule):
    id = "pagination_sequence_error"
    name = "Pagination Sequence Error"
    category = "Pagination"
    severity = "warning"
    description = "Error de orden lÃ³gico en la secuencia paginada (ej. salto de page 2 -> 5)."
    fix_guidance = (
        "Verifica que rel=next/prev formen una secuencia continua: "
        "page 1 -> page 2 -> page 3, sin saltos ni gaps. Saltos en "
        "la secuencia rompen el descubrimiento."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading",
    ]
    # TODO(schema): needs pagination_links table.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
