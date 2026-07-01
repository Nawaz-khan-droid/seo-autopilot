"""Noindex Multiple.

# TODO(schema): requires count of meta robots tags per URL (currently we
only store the parsed/concatenated value in `meta_robots`).
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NoindexMultiple(Rule):
    id = "noindex_multiple"
    name = "Noindex Multiple"
    category = "Directives"
    severity = "warning"
    description = (
        "Existen mÃºltiples meta robots con `noindex` en la misma URL. "
        "Google puede tener comportamiento impredecible si hay duplicados."
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
