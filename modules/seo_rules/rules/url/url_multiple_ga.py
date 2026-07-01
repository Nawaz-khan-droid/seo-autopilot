"""Multiple GA codes.

# TODO(schema): requires extracting Google Analytics IDs (UA-/G-/MO-) from
# the page. No column exposes this today.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlMultipleGa(Rule):
    id = "url_multiple_ga"
    name = "Multiple GA codes"
    category = "URL"
    severity = "warning"
    description = "PÃ¡gina con dos o mÃ¡s IDs de Google Analytics."
    fix_guidance = (
        "MantÃ©n una Ãºnica instalaciÃ³n de Google Analytics por pÃ¡gina para "
        "evitar duplicaciÃ³n de hits y mÃ©tricas inconsistentes."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]
    enabled_by_default = False  # awaiting GA tracking-id extraction

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder â€” needs GA tracking-id extraction
        return iter([])
