"""Resource redirects to itself.

# TODO(schema): requires resource-level redirect tracking.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ResourceRedirectSelf(Rule):
    id = "resource_redirect_self"
    name = "Resource redirects to itself"
    category = "Response Codes"
    severity = "warning"
    description = "Recurso (imagen/CSS/JS) que redirige a sÃ­ mismo."
    fix_guidance = (
        "Auto-redirect en un recurso indica una regla de servidor mal configurada. "
        "Revisa la config de Apache/Nginx/CDN y elimina la regla degenerada."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs resource-level redirect tracking
        return iter([])
