"""Head Invalid HTML.

# TODO(schema): requires parser-level detection of invalid <head>
contents (tags that prematurely close the head).
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HeadInvalidHtml(Rule):
    id = "head_invalid_html"
    name = "Head Invalid HTML"
    category = "Directives"
    severity = "warning"
    description = (
        "El `<head>` contiene HTML invÃ¡lido (e.g. tags de body como <div>, "
        "<p>, etc.) que el parser puede interpretar como cierre del head."
    )
    fix_guidance = (
        "Mueve cualquier elemento de body fuera del `<head>`. Solo se "
        "permiten meta, link, title, style, script, base, noscript."
    )
    references = [
        "https://html.spec.whatwg.org/multipage/semantics.html#the-head-element",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” requires <head>-level HTML validation
        return iter([])
