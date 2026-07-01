"""Image-link without alt text.

# TODO(schema): requires the image-anchor relation (which <a> wraps which <img>).
The schema's `links` and `resources` tables aren't joined by parent-anchor:
we'd need a `parent_link_id` column on resources, or a dedicated table mapping
images to the wrapping anchor. Without that, we cannot distinguish a plain
<img> from one inside an <a> link.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ImageAnchoredNoAlt(Rule):
    id = "image_anchored_no_alt"
    name = "Image-Link Without Alt"
    category = "Images"
    severity = "warning"
    description = "Imagen dentro de <a> sin alt text (anchor sin texto accesible)."
    fix_guidance = (
        "Si la imagen es el Ãºnico contenido del enlace, su alt actÃºa como anchor "
        "text. AÃ±ade alt descriptivo del destino del link, no solo de la imagen."
    )
    references = [
        "https://www.w3.org/WAI/tutorials/images/functional/",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs image-anchor parent relation
        return iter([])
