"""TODO(schema): requires DOM position of the canonical tag (inside <head>
vs <body>). The current schema only stores the resolved value."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalOutsideHead(Rule):
    id = "canonical_outside_head"
    name = "Canonical Outside Head"
    category = "Canonicals"
    severity = "critical"
    description = "El canonical aparece fuera del <head>."
    fix_guidance = (
        "Mueve la etiqueta <link rel=\"canonical\"> dentro del <head>. "
        "Google ignora canonicals colocados en <body> o cualquier otro "
        "lugar del documento."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.canonical_in_head BOOLEAN column.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
