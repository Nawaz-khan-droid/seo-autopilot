"""TODO(schema): requires preservation of the canonical tag's attributes."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalSuperfluousAttrs(Rule):
    id = "canonical_superfluous_attrs"
    name = "Canonical Superfluous Attributes"
    category = "Canonicals"
    severity = "info"
    description = "La etiqueta canonical contiene atributos innecesarios."
    fix_guidance = (
        "Elimina atributos superfluos de <link rel=\"canonical\">. La "
        "forma estÃ¡ndar es: <link rel=\"canonical\" href=\"...\">. "
        "Cualquier otro atributo (hreflang, type, media...) es inÃºtil."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.canonical_attrs JSON column.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
