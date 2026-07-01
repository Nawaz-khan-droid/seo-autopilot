"""Font too small for mobile.

# TODO(rendered): requires computed CSS font-size per text element.
Schema does not store rendered font sizes.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class FontTooSmallMobile(Rule):
    id = "font_too_small_mobile"
    name = "Font Too Small For Mobile"
    category = "Mobile"
    severity = "warning"
    description = "Texto con tamaÃ±o de fuente inferior a 12 px en mÃ³vil."
    fix_guidance = (
        "Aumenta el font-size base a â‰¥16px y nunca uses <12px en mÃ³vil. "
        "Google Mobile-Friendly Test marca esto explÃ­citamente."
    )
    references = [
        "https://web.dev/font-size/",
    ]
    enabled_by_default = False
    requires_rendered_html = True

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs computed font-size per text node
        return iter([])
