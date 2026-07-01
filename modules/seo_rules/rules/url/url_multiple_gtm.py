"""Multiple GTM codes.

# TODO(schema): requires extracting GTM container IDs from the page (script
# tags or noscript fragments). No column or table exposes this today.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlMultipleGtm(Rule):
    id = "url_multiple_gtm"
    name = "Multiple GTM codes"
    category = "URL"
    severity = "warning"
    description = "PÃ¡gina con dos o mÃ¡s contenedores Google Tag Manager (GTM)."
    fix_guidance = (
        "Consolida en un Ãºnico contenedor GTM por pÃ¡gina. MÃºltiples "
        "contenedores generan duplicaciÃ³n de eventos y problemas de mediciÃ³n."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]
    enabled_by_default = False  # awaiting GTM container extraction

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder â€” needs GTM container ID extraction
        return iter([])
