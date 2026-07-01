"""Broken Bookmark.

# TODO(schema): requires tracking link fragments and matching them against
# anchors / IDs in the destination page. We don't currently store fragment
# identifiers on `links` nor extract `id`/`name` anchors from the body.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class BrokenBookmark(Rule):
    id = "broken_bookmark"
    name = "Broken Bookmark"
    category = "URL"
    severity = "warning"
    description = (
        "Link con fragment `#anchor` que no existe como `id`/`name` en la "
        "pÃ¡gina destino."
    )
    fix_guidance = (
        "AsegÃºrate de que cada `<a href=\"#foo\">` tenga su correspondiente "
        "elemento `id=\"foo\"` (o `name=\"foo\"` legacy) en la pÃ¡gina destino."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]
    enabled_by_default = False  # awaiting fragment + anchor extraction

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder â€” needs fragment tracking on links + DOM anchor index
        return iter([])
