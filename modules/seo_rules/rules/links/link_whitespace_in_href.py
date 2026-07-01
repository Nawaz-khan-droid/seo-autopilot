"""Link whitespace in href rule.

# TODO(schema): the canonicalisation step at crawl time strips whitespace from
# href values, so the original raw href is not preserved. Mark as
# placeholder until raw_href is stored.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class LinkWhitespaceInHref(Rule):
    id = "link_whitespace_in_href"
    name = "Link Whitespace In Href"
    category = "Links"
    severity = "warning"
    description = "Atributo href con espacios en blanco al inicio, fin o medio."
    fix_guidance = "Elimina los espacios en blanco del atributo href."
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder: needs raw_href column
        return iter([])
