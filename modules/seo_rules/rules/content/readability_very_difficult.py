"""Readability very difficult rule.

# TODO(schema): readability metrics not stored.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ReadabilityVeryDifficult(Rule):
    id = "readability_very_difficult"
    name = "Readability Very Difficult"
    category = "Content"
    severity = "info"
    description = "PÃ¡ginas con legibilidad muy difÃ­cil (requiere puntuaciÃ³n tipo Flesch)."
    fix_guidance = "Reescribe el texto en un nivel de lectura mÃ¡s accesible."
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder: needs readability score column
        return iter([])
