"""External 5XX.

# TODO(schema): requires crawling external links to obtain their status code.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class External5xx(Rule):
    id = "external_5xx"
    name = "External 5XX"
    category = "Response Codes"
    severity = "warning"
    description = "Enlace saliente que apunta a una URL externa con error 5XX."
    fix_guidance = (
        "El servidor externo estÃ¡ fallando. Considera sustituir el enlace por otro "
        "recurso fiable. Si es transitorio, vuelve a verificarlo en otro crawl."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” externals not crawled
        return iter([])
