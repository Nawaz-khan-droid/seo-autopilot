"""Image alt text repeats surrounding/adjacent text.

# TODO(schema): requires DOM-adjacent text capture per image.
The schema doesn't store text that surrounds each <img> (e.g. caption,
preceding heading, sibling paragraph). To detect alt-redundancy we'd need
either the rendered DOM context or a `surrounding_text` column on resources.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ImageAltRepeatsText(Rule):
    id = "image_alt_repeats_text"
    name = "Image Alt Repeats Adjacent Text"
    category = "Images"
    severity = "info"
    description = "Alt text repite literalmente texto adyacente (caption, pÃ¡rrafo)."
    fix_guidance = (
        "El alt no debe duplicar el texto visible cercano: los lectores de "
        "pantalla lo leerÃ­an dos veces. Si la imagen estÃ¡ descrita en un "
        "<figcaption> o el pÃ¡rrafo inmediato, deja alt='' o describe algo "
        "complementario."
    )
    references = [
        "https://www.w3.org/WAI/tutorials/images/decorative/",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs surrounding text per image
        return iter([])
