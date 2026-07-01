"""No GTM code.

# TODO(schema): requires extracting GTM container IDs from the page.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlNoGtm(Rule):
    id = "url_no_gtm"
    name = "No GTM code"
    category = "URL"
    severity = "info"
    description = "PÃ¡gina sin contenedor Google Tag Manager."
    fix_guidance = (
        "Si tu sitio depende de GTM para tracking, asegÃºrate de que el "
        "snippet estÃ© en el <head> de TODAS las pÃ¡ginas (incluido 404)."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]
    enabled_by_default = False  # awaiting GTM container extraction

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder â€” needs GTM container ID extraction
        return iter([])
