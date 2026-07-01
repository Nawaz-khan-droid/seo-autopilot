"""Robots Meta Outside Head.

# TODO(schema): requires DOM-position of meta tags (i.e. whether the
robots meta is inside <head> or not). Crawler currently exposes only the
parsed `meta_robots` value.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class RobotsMetaOutsideHead(Rule):
    id = "robots_meta_outside_head"
    name = "Robots Meta Outside Head"
    category = "Directives"
    severity = "warning"
    description = (
        "El `<meta name=\"robots\">` aparece fuera del `<head>`. Google "
        "puede ignorarlo cuando aparece en el `<body>`."
    )
    fix_guidance = (
        "Mueve el `<meta name=\"robots\">` al `<head>` antes de cualquier "
        "cierre de etiqueta accidental que lo expulse del head."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet track DOM position of meta
        return iter([])
