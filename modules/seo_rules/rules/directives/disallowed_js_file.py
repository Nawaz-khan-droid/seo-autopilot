"""Disallowed JS File.

# TODO(schema): requires cross-referencing referenced JS resources against
robots.txt rules. We do not currently mark resources as `from_robots`.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class DisallowedJsFile(Rule):
    id = "disallowed_js_file"
    name = "Disallowed JS File"
    category = "Directives"
    severity = "warning"
    description = (
        "Un archivo JavaScript referenciado por la pÃ¡gina estÃ¡ bloqueado "
        "por robots.txt, lo que puede impedir el correcto renderizado por "
        "parte de Google."
    )
    fix_guidance = (
        "Permite el rastreo de los archivos JS crÃ­ticos para el render. "
        "Google necesita ejecutar JS para entender la pÃ¡gina completa."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” resources don't track from_robots yet
        return iter([])
