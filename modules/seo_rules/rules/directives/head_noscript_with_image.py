"""Head Noscript With Image.

# TODO(schema): requires parsing of <head> contents (specifically the
detection of <noscript> with an <img> inside, which closes <head>
prematurely in WHATWG HTML).
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HeadNoscriptWithImage(Rule):
    id = "head_noscript_with_image"
    name = "Head Noscript With Image"
    category = "Directives"
    severity = "warning"
    description = (
        "El `<head>` contiene un `<noscript>` con una imagen, lo que cierra "
        "el `<head>` prematuramente y puede expulsar directivas robots, "
        "canonical o hreflang al `<body>`."
    )
    fix_guidance = (
        "Mueve los `<noscript>` con imagen al `<body>` o asegÃºrate de que "
        "todos los meta crÃ­ticos aparecen antes del `<noscript>`."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet parse <head> contents
        return iter([])
