"""Nofollow Multiple.

# TODO(schema): requires count of meta robots tags per URL.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NofollowMultiple(Rule):
    id = "nofollow_multiple"
    name = "Nofollow Multiple"
    category = "Directives"
    severity = "warning"
    description = (
        "Existen mÃºltiples meta robots con `nofollow` en la misma URL."
    )
    fix_guidance = (
        "MantÃ©n una Ãºnica declaraciÃ³n `<meta name=\"robots\">` en el `<head>`."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet count meta tags per URL
        return iter([])
