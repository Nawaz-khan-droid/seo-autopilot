"""TODO(schema): requires list of all <base href> values from HTML."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class BaseUrlMultipleMismatched(Rule):
    id = "base_url_multiple_mismatched"
    name = "Multiple Mismatched Base URLs"
    category = "Canonicals"
    severity = "info"
    description = "MÃºltiples <base> con valores diferentes."
    fix_guidance = (
        "Deja una Ãºnica <base> en el <head>. MÃºltiples <base> con "
        "valores distintos son contradictorias; el navegador solo "
        "respeta la primera."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.base_urls VARCHAR[] column.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
