"""Disallowed Image.

# TODO(schema): requires cross-referencing image resources against
robots.txt rules.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class DisallowedImage(Rule):
    id = "disallowed_image"
    name = "Disallowed Image"
    category = "Directives"
    severity = "warning"
    description = (
        "Una imagen referenciada en la pÃ¡gina estÃ¡ bloqueada por robots.txt, "
        "lo que la excluye de Google Images."
    )
    fix_guidance = (
        "Permite el rastreo de imÃ¡genes que quieras ver en Google Images. "
        "Solo bloquea cuando las imÃ¡genes sean privadas/sensibles."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” resources don't track from_robots yet
        return iter([])
