"""Resource in chained redirect loop.

# TODO(schema): requires resource-level redirect tracking with chain/loop info.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ResourceRedirectChainLoop(Rule):
    id = "resource_redirect_chain_loop"
    name = "Resource in chained redirect loop"
    category = "Response Codes"
    severity = "warning"
    description = "Recurso atrapado en un loop de redirecciones."
    fix_guidance = (
        "Revisa las reglas de redirect del CDN y/o servidor â€” un recurso nunca deberÃ­a "
        "entrar en bucle. Apunta directamente a la URL final."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs resource-level redirect tracking
        return iter([])
