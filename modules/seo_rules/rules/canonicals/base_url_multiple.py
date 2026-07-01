"""TODO(schema): requires count of <base> tags in HTML."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class BaseUrlMultiple(Rule):
    id = "base_url_multiple"
    name = "Multiple Base URLs"
    category = "Canonicals"
    severity = "info"
    description = "MÃºltiples etiquetas <base> declaradas en la misma pÃ¡gina."
    fix_guidance = (
        "Deja una Ãºnica etiqueta <base> en el <head>. HTML solo "
        "reconoce la primera; las demÃ¡s se ignoran y son ruido."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.base_url_count INTEGER column.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
