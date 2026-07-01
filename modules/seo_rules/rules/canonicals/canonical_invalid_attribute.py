"""TODO(schema): requires preservation of the canonical tag's attributes
(rel, href, ...) for validation. Currently only href is persisted."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalInvalidAttribute(Rule):
    id = "canonical_invalid_attribute"
    name = "Canonical Invalid Attribute"
    category = "Canonicals"
    severity = "warning"
    description = "La etiqueta canonical contiene atributos HTML invÃ¡lidos."
    fix_guidance = (
        "Revisa la sintaxis del <link rel=\"canonical\" href=\"...\"> y "
        "elimina cualquier atributo no estÃ¡ndar o malformado."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.canonical_attrs JSON column with raw attributes.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
