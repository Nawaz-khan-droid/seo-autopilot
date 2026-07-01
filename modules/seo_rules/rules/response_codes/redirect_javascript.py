"""JavaScript redirect detection.

# TODO(schema): requires a `redirect_type` column in `redirects` populated when
# the headless renderer detects window.location / history.replaceState
# triggered redirects.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class RedirectJavascript(Rule):
    id = "redirect_javascript"
    name = "JavaScript redirect"
    category = "Response Codes"
    severity = "info"
    description = "URL redirige mediante JavaScript (window.location, etc.)."
    fix_guidance = (
        "Migra a redirecciÃ³n 301 a nivel de servidor siempre que sea posible. "
        "Google maneja redirecciones JS pero con coste y riesgo: requieren render, "
        "consumen crawl budget y pueden no transmitir seÃ±ales si fallan."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics",
    ]
    enabled_by_default = False
    requires_rendered_html = True

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet differentiate redirect types
        return iter([])
