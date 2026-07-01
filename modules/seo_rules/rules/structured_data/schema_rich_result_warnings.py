from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SchemaRichResultWarnings(Rule):
    id = "schema_rich_result_warnings"
    name = "Rich Result Validation Warnings"
    category = "Structured Data"
    severity = "info"
    enabled_by_default = False  # TODO(schema): rich result warnings no rastreado aparte
    description = "Structured data con warnings de Rich Results."
    fix_guidance = (
        "Atiende los warnings del Rich Results Test para optimizar la "
        "presentaciÃ³n en SERPs."
    )
    references = [
        "https://schema.org/",
        "https://developers.google.com/search/docs/appearance/structured-data",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # TODO(schema): need separate rich-result warnings column
        return iter([])
