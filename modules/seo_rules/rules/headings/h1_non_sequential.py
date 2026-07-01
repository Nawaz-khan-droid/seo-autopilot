"""H1 non-sequential placement.

# TODO(schema): the schema stores h1..h6 as separate text arrays without DOM
# order or document position, so we cannot detect that an <h1> appears after
# another heading level. Re-enable when an extractor adds an ordered
# `headings` table with (level, position, text) tuples.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class H1NonSequential(Rule):
    id = "h1_non_sequential"
    name = "H1 Non-sequential"
    category = "Headings"
    severity = "info"
    description = (
        "El <h1> aparece despuÃ©s de otros encabezados o en posiciÃ³n no inicial "
        "(no detectable con el schema actual)."
    )
    fix_guidance = (
        "Coloca el <h1> al principio del contenido principal, antes de cualquier <h2> o inferior."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” heading hierarchy not tracked
        return iter([])
