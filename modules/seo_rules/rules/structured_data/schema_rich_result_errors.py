from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SchemaRichResultErrors(Rule):
    id = "schema_rich_result_errors"
    name = "Rich Result Validation Errors"
    category = "Structured Data"
    severity = "warning"
    enabled_by_default = False  # TODO(schema): rich result validation no rastreado aparte
    description = (
        "Structured data falla los requisitos de Google Rich Results."
    )
    fix_guidance = (
        "Usa el Rich Results Test de Google y arregla los campos requeridos "
        "marcados como error."
    )
    references = [
        "https://schema.org/",
        "https://developers.google.com/search/docs/appearance/structured-data",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # TODO(schema): need separate rich-result validation column
        return iter([])
