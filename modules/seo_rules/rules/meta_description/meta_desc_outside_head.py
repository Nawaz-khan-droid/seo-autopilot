"""Meta description placed outside <head>.

# TODO(schema): the schema does not record DOM position of meta tags, so we
# cannot tell whether <meta name="description"> appeared inside <head> or
# elsewhere. Re-enable when an extractor flag (e.g.
# `meta_description_in_head BOOLEAN`) lands.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MetaDescOutsideHead(Rule):
    id = "meta_desc_outside_head"
    name = "Meta Description Outside <head>"
    category = "Meta Description"
    severity = "warning"
    description = (
        "El <meta name=\"description\"> aparece fuera de <head> y los "
        "buscadores pueden ignorarlo (no detectable con el schema actual)."
    )
    fix_guidance = (
        "Coloca el <meta name=\"description\"> dentro de <head>, antes del cierre </head>."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/snippet",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not track DOM position of meta tags
        return iter([])
