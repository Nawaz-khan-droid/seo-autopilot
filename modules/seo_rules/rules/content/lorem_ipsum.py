"""Lorem Ipsum placeholder rule.

# TODO(schema): body text is not persisted by default. raw_html is available
# only when persist_html=True, and BLOB scans on every URL are expensive.
# Marking as not enabled by default.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class LoremIpsum(Rule):
    id = "lorem_ipsum"
    name = "Lorem Ipsum Placeholder"
    category = "Content"
    severity = "warning"
    description = "Texto placeholder Lorem Ipsum detectado en pÃ¡gina live."
    fix_guidance = "Reemplaza el texto placeholder con copy real antes de publicar."
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder: scanning raw_html BLOB for "lorem ipsum" is too slow
        # without a body_text column.
        return iter([])
