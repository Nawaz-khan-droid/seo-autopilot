"""Tap targets too small.

# TODO(rendered): requires rendered bounding-box per interactive element.
Detection compares interactive element sizes (â‰¥48x48 px recommended) and the
spacing between adjacent targets. Needs rendered layout.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class TapTargetsTooSmall(Rule):
    id = "tap_targets_too_small"
    name = "Tap Targets Too Small"
    category = "Mobile"
    severity = "warning"
    description = (
        "Botones/enlaces tÃ¡ctiles mÃ¡s pequeÃ±os que 48x48 px o demasiado juntos."
    )
    fix_guidance = (
        "Asegura tap targets de mÃ­nimo 48x48 CSS px y separaciÃ³n >8 px entre "
        "ellos. Google Mobile-Friendly Test marca este patrÃ³n."
    )
    references = [
        "https://web.dev/tap-targets/",
    ]
    enabled_by_default = False
    requires_rendered_html = True

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs rendered tap-target bounding boxes
        return iter([])
