"""Spelling errors rule.

# TODO(schema): we don't have a spell-check pass nor body text stored. The
# rule remains as a placeholder until a spell-checking column or pipeline
# is added.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SpellingErrors(Rule):
    id = "spelling_errors"
    name = "Spelling Errors"
    category = "Content"
    severity = "info"
    description = "PÃ¡ginas con errores ortogrÃ¡ficos (requiere spell-check)."
    fix_guidance = "Revisa con un corrector ortogrÃ¡fico el contenido marcado."
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder: needs spell-check column in schema
        return iter([])
