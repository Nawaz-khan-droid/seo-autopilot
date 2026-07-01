"""Meta description over ~985 pixels.

# TODO(schema): the schema does not store rendered pixel width of meta
# descriptions and we have no font-metrics module yet. Re-enable when an
# extractor adds a numeric `meta_description_pixels INTEGER` column or a
# helper utility lands.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_PIXELS = 985


@register_rule
class MetaDescOver985Pixels(Rule):
    id = "meta_desc_over_985_pixels"
    name = "Meta Description Over 985 Pixels"
    category = "Meta Description"
    severity = "info"
    description = (
        f"Meta description con mÃ¡s de {THRESHOLD_PIXELS} pÃ­xeles renderizados "
        f"(no detectable con el schema actual)."
    )
    fix_guidance = (
        f"Acorta la meta description para que ocupe menos de {THRESHOLD_PIXELS} "
        f"pÃ­xeles en el SERP de Google."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/snippet",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” no pixel-width data in schema yet
        return iter([])
