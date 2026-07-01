"""Broken/invalid HTML rule.

# TODO(schema): no HTML validity flag is stored. Would require running an
# HTML validator over raw_html or a dedicated column.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class BrokenInvalidHtml(Rule):
    id = "broken_invalid_html"
    name = "Broken Or Invalid HTML"
    category = "Content"
    severity = "warning"
    description = "PÃ¡ginas con HTML mal formado o invÃ¡lido."
    fix_guidance = "Pasa el HTML por un validador (W3C/lxml) y corrige los errores reportados."
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder: needs html_valid column
        return iter([])
