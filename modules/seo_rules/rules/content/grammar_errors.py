"""Grammar errors rule.

# TODO(schema): we don't have grammar checks nor body text stored.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class GrammarErrors(Rule):
    id = "grammar_errors"
    name = "Grammar Errors"
    category = "Content"
    severity = "info"
    description = "PÃ¡ginas con errores gramaticales (requiere anÃ¡lisis gramatical)."
    fix_guidance = "Revisa con un corrector gramatical el contenido marcado."
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder: needs grammar-check column
        return iter([])
