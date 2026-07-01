"""External redirected.

# TODO(schema): requires fetching external links to detect 3xx responses.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ExternalRedirected(Rule):
    id = "external_redirected"
    name = "External redirected"
    category = "Response Codes"
    severity = "info"
    description = "Enlace saliente que pasa por una redirecciÃ³n antes de llegar al destino."
    fix_guidance = (
        "Actualiza el enlace para apuntar directamente a la URL final externa. "
        "Reduce un salto innecesario y evita depender de que el redirect siga vigente."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” externals not crawled
        return iter([])
