"""Resource redirect broken.

# TODO(schema): requires resource-level redirect tracking. The `resources`
# table holds final status but not the chain. We need to either reuse
# `redirects` keyed on resource URLs or add a redirect_chain field on
# `resources`.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ResourceRedirectBroken(Rule):
    id = "resource_redirect_broken"
    name = "Resource redirect broken"
    category = "Response Codes"
    severity = "warning"
    description = "Recurso (imagen/CSS/JS) redirige a un destino 4XX/5XX."
    fix_guidance = (
        "Actualiza la URL del recurso en el HTML para apuntar directamente al destino "
        "final que sÃ­ responde, o sustituye el recurso roto."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs resource-level redirect tracking
        return iter([])
