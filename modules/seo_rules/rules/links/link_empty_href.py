"""Link empty href rule.

# TODO(schema): empty hrefs are filtered out during link extraction, so the
# distinction between "missing href" and "href=''" is not preserved. Use
# `link_malformed_href` for the available signal.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class LinkEmptyHref(Rule):
    id = "link_empty_href"
    name = "Link Empty Href"
    category = "Links"
    severity = "info"
    description = "Atributo href presente pero vacÃ­o en el HTML."
    fix_guidance = "Elimina el href o sustitÃºyelo por una URL vÃ¡lida."
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder: extraction filters these out before storage
        return iter([])
