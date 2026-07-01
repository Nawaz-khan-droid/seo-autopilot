from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SchemaParseErrors(Rule):
    id = "schema_parse_errors"
    name = "Structured Data Parse Errors"
    category = "Structured Data"
    severity = "warning"
    enabled_by_default = False  # TODO(schema): no diferenciamos parse vs validation errors
    description = (
        "Structured data con errores de parsing (JSON malformado, sintaxis "
        "incorrecta de Microdata/RDFa)."
    )
    fix_guidance = (
        "Valida la sintaxis JSON con un validador online. Para Microdata/RDFa, "
        "verifica que los atributos itemscope/itemtype/typeof sean correctos."
    )
    references = [
        "https://schema.org/",
        "https://developers.google.com/search/docs/appearance/structured-data",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # TODO(schema): need separate flag for parse vs validation errors
        return iter([])
