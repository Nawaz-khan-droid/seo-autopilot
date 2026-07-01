"""H2 non-sequential placement.

# TODO(schema): the schema stores h2 as a flat array without DOM order
# relative to other heading levels, so we cannot detect that an <h2> appears
# before <h1> or other irregular ordering. Re-enable when the extractor adds
# an ordered `headings` table with (level, position, text).
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class H2NonSequential(Rule):
    id = "h2_non_sequential"
    name = "H2 Non-sequential"
    category = "Headings"
    severity = "info"
    description = (
        "Los <h2> aparecen en posiciÃ³n no secuencial respecto a otros encabezados "
        "(no detectable con el schema actual)."
    )
    fix_guidance = (
        "Asegura que los <h2> estÃ©n siempre dentro de la jerarquÃ­a esperada: despuÃ©s "
        "del <h1> y antes de cualquier <h3> que les corresponda."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” heading hierarchy not tracked
        return iter([])
