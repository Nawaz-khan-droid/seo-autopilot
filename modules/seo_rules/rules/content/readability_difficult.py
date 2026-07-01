"""Readability difficult rule.

# TODO(schema): readability metrics (Flesch, etc.) not stored.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ReadabilityDifficult(Rule):
    id = "readability_difficult"
    name = "Readability Difficult"
    category = "Content"
    severity = "info"
    description = "PÃ¡ginas con legibilidad difÃ­cil (requiere puntuaciÃ³n tipo Flesch)."
    fix_guidance = "Simplifica frases y vocabulario para mejorar la legibilidad."
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder: needs readability score column
        return iter([])
