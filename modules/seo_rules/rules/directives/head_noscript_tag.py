"""Head Noscript Tag.

# TODO(schema): requires detecting <noscript> tags inside <head> (info
diagnostic â€” they're allowed but can hide content from Google).
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HeadNoscriptTag(Rule):
    id = "head_noscript_tag"
    name = "Head Noscript Tag"
    category = "Directives"
    severity = "info"
    description = (
        "El `<head>` contiene un `<noscript>`. Aunque estÃ¡ permitido, su "
        "uso indebido puede romper el procesamiento de directivas posteriores."
    )
    fix_guidance = (
        "Verifica que el `<noscript>` solo contiene metas/links permitidos "
        "y no introduce HTML que cierre el `<head>` prematuramente."
    )
    references = [
        "https://html.spec.whatwg.org/multipage/scripting.html#the-noscript-element",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet parse <head> contents
        return iter([])
