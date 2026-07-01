"""Image map (<map>) present.

# TODO(schema): requires <map>/<area> tag tracking.
Image maps are legacy and not tracked in the current schema.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ImageMapPresent(Rule):
    id = "image_map_present"
    name = "Image Map Present"
    category = "Mobile"
    severity = "info"
    description = "PÃ¡gina usa <map> / <area> (image maps), patrÃ³n problemÃ¡tico en mÃ³vil."
    fix_guidance = (
        "Reemplaza el image map por una soluciÃ³n CSS/SVG con Ã¡reas clicables "
        "individuales. Los <area> son difÃ­ciles de tocar con el dedo y poco "
        "accesibles."
    )
    references = [
        "https://web.dev/articles/responsive-web-design-basics",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs <map>/<area> tracking
        return iter([])
