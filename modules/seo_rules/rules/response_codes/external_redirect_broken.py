"""External redirect broken.

# TODO(schema): requires following external redirect chains and storing the
# destination status code. Externals not crawled today.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ExternalRedirectBroken(Rule):
    id = "external_redirect_broken"
    name = "External redirect broken"
    category = "Response Codes"
    severity = "warning"
    description = "URL externa redirige a un destino 4XX/5XX."
    fix_guidance = (
        "El enlace externo termina en una URL rota tras seguir redirects. SustitÃºyelo "
        "por la URL final correcta, o elimÃ­nalo si el recurso ya no existe."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” externals not crawled
        return iter([])
