"""TODO(schema): requires rel=next/prev metadata to detect a single URL
participating in multiple paginated sequences."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class PaginationMultiple(Rule):
    id = "pagination_multiple"
    name = "Multiple Pagination URLs"
    category = "Pagination"
    severity = "info"
    description = "Una URL participa en mÃºltiples secuencias de paginaciÃ³n."
    fix_guidance = (
        "Una URL deberÃ­a pertenecer a una Ãºnica secuencia paginada. "
        "MÃºltiples rel=next/prev conflictivos confunden a los crawlers."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading",
    ]
    # TODO(schema): needs pagination_links table.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
