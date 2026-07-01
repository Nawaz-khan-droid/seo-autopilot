"""HTTP Refresh redirect detection.

# TODO(schema): requires a `redirect_type` column in `redirects`.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class RedirectHttpRefresh(Rule):
    id = "redirect_http_refresh"
    name = "HTTP Refresh redirect"
    category = "Response Codes"
    severity = "info"
    description = "URL redirige usando el header HTTP `Refresh:` en vez de un 3xx."
    fix_guidance = (
        "Sustituye el header HTTP Refresh por una redirecciÃ³n 301 estÃ¡ndar. "
        "Es un mecanismo legacy (Netscape) que algunos crawlers no procesan correctamente."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet differentiate redirect types
        return iter([])
