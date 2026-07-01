"""Meta description below ~400 pixels.

# TODO(schema): the schema does not store rendered pixel width of meta
# descriptions. Re-enable when an extractor adds a numeric
# `meta_description_pixels INTEGER` column.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

THRESHOLD_PIXELS = 400


@register_rule
class MetaDescBelow400Pixels(Rule):
    id = "meta_desc_below_400_pixels"
    name = "Meta Description Below 400 Pixels"
    category = "Meta Description"
    severity = "info"
    description = (
        f"Meta description con menos de {THRESHOLD_PIXELS} pÃ­xeles renderizados "
        f"(no detectable con el schema actual)."
    )
    fix_guidance = (
        f"Expande la meta description con detalle relevante para superar los "
        f"{THRESHOLD_PIXELS} pÃ­xeles y ocupar mÃ¡s superficie en el SERP."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/snippet",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” no pixel-width data in schema yet
        return iter([])
