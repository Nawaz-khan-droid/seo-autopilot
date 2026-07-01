"""External No Response.

# TODO(schema): requires crawling external links and storing their response.
# Currently externals are not fetched.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ExternalNoResponse(Rule):
    id = "external_no_response"
    name = "External No Response"
    category = "Response Codes"
    severity = "info"
    description = "URL externa enlazada que no respondiÃ³ durante el crawl."
    fix_guidance = (
        "El destino externo estÃ¡ caÃ­do o bloqueando crawlers. Si el enlace ya no es Ãºtil, "
        "elimÃ­nalo o sustitÃºyelo. Los enlaces a recursos no disponibles degradan la "
        "experiencia y pueden ser seÃ±al dÃ©bil de baja calidad."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” externals not crawled
        return iter([])
