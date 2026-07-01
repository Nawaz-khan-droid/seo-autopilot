"""Noindex Only In Source (HTML rendered diff).

# TODO(schema): requires diff between raw HTML meta robots and rendered
HTML meta robots. Crawler does not currently parse meta_robots
separately for raw vs rendered.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NoindexOnlyInSource(Rule):
    id = "noindex_only_in_source"
    name = "Noindex Only In Source"
    category = "Directives"
    severity = "warning"
    description = (
        "El `noindex` aparece en el HTML inicial (source) pero JavaScript lo "
        "elimina al renderizar. Google indexarÃ¡ la pÃ¡gina renderizada."
    )
    fix_guidance = (
        "Decide si la pÃ¡gina debe indexarse o no, y aplica la directiva de "
        "forma consistente en source y rendered."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]
    enabled_by_default = False
    requires_rendered_html = True

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet split source/rendered meta
        return iter([])
