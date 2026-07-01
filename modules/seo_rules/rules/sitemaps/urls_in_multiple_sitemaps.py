"""URLs In Multiple Sitemaps.

# TODO(schema): requires tracking N-to-N URL â†” sitemap relationships
(currently `urls.from_sitemap` is just a boolean â€” we don't know which
sitemap or how many).
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlsInMultipleSitemaps(Rule):
    id = "urls_in_multiple_sitemaps"
    name = "URLs In Multiple Sitemaps"
    category = "Sitemaps"
    severity = "info"
    description = (
        "Una misma URL aparece en mÃ¡s de un sitemap.xml. Aunque el "
        "protocolo lo permite, suele ser seÃ±al de configuraciÃ³n inconsistente."
    )
    fix_guidance = (
        "MantÃ©n cada URL en un Ãºnico sitemap. Si usas sitemap-index, asegÃºrate "
        "de que los sitemaps hijos no se solapan."
    )
    references = [
        "https://www.sitemaps.org/protocol.html",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema only stores boolean from_sitemap
        return iter([])
