"""Missing X-Content-Type-Options.

# TODO(schema): requires a `header_x_content_type_options` column on `urls`
# (only header_csp / header_hsts / header_x_frame_options / header_referrer_policy
# are extracted today).
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MissingXContentTypeOptions(Rule):
    id = "missing_x_content_type_options"
    name = "Missing X-Content-Type-Options"
    category = "Security"
    severity = "info"
    description = (
        "Respuesta sin header `X-Content-Type-Options: nosniff`. Permite "
        "MIME-sniffing en algunos navegadores."
    )
    fix_guidance = "Configura `X-Content-Type-Options: nosniff` en todas las respuestas."
    references = [
        "https://developer.mozilla.org/docs/Web/HTTP/Headers/X-Content-Type-Options",
    ]
    enabled_by_default = False  # awaiting header_x_content_type_options column

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder â€” needs schema column
        return iter([])
