"""Nofollow Only In Source (HTML rendered diff).

# TODO(schema): requires diff between raw and rendered meta robots.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NofollowOnlyInSource(Rule):
    id = "nofollow_only_in_source"
    name = "Nofollow Only In Source"
    category = "Directives"
    severity = "warning"
    description = (
        "El `nofollow` aparece en el HTML inicial pero no en el HTML "
        "renderizado tras ejecutar JavaScript."
    )
    fix_guidance = (
        "Aplica la directiva de forma coherente en source y rendered HTML."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]
    enabled_by_default = False
    requires_rendered_html = True

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet split source/rendered meta
        return iter([])
