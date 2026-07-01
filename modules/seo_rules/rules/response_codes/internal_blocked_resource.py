"""Internal Blocked Resource (CSS/JS/imagen interna bloqueada).

# TODO(schema): requires distinguishing 'page' vs 'resource' rows. Currently
# `urls` mixes them; we need either a `resource_type` column on `urls` or a
# join with `resources` populated with status codes for blocked entries.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalBlockedResource(Rule):
    id = "internal_blocked_resource"
    name = "Internal Blocked Resource"
    category = "Response Codes"
    severity = "warning"
    description = "Recurso interno (CSS/JS/imagen) bloqueado por robots.txt."
    fix_guidance = (
        "Bloquear CSS o JS impide a Google renderizar correctamente la pÃ¡gina y puede "
        "afectar al ranking. Permite el crawl de los recursos crÃ­ticos en robots.txt."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs page-vs-resource distinction
        return iter([])
