"""Background images accessibility check.

# TODO(schema): requires CSS background-image extraction (not yet tracked).
The schema's `resources` table only captures `<img>` and equivalent referenced
files. Detecting `background-image: url(...)` would require a CSS parser
extension to the engine.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ImageBackgroundA11y(Rule):
    id = "image_background_a11y"
    name = "Background Images A11y"
    category = "Images"
    severity = "info"
    description = (
        "Imagen de fondo CSS posiblemente inaccesible (sin alternativa textual)."
    )
    fix_guidance = (
        "Si la imagen es decorativa dÃ©jala como background-image. Si transmite "
        "informaciÃ³n, usa <img alt> en su lugar para que sea accesible."
    )
    references = [
        "https://web.dev/articles/serve-images-webp",
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” engine doesn't yet extract CSS background-image
        return iter([])
