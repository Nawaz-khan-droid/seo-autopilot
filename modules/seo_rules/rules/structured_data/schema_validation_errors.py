from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SchemaValidationErrors(Rule):
    id = "schema_validation_errors"
    name = "Structured Data Validation Errors"
    category = "Structured Data"
    severity = "warning"
    description = "Structured data presente con errores de validaciÃ³n schema.org."
    fix_guidance = (
        "Revisa el JSON-LD/Microdata/RDFa y corrige los errores de validaciÃ³n. "
        "Usa el Rich Results Test de Google para verificar."
    )
    references = [
        "https://schema.org/",
        "https://developers.google.com/search/docs/appearance/structured-data",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT s.url_id, u.url, s.syntax, s.schema_type, s.validation_errors
            FROM structured_data s
            LEFT JOIN urls u ON u.url_id = s.url_id
            WHERE s.valid = FALSE
            """
        ).fetchall()
        for url_id, url, syntax, schema_type, errors in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "syntax": syntax,
                    "schema_type": schema_type,
                    "errors": list(errors) if errors else [],
                },
                message=f"{url} tiene errores de structured data ({schema_type}, {syntax})",
            )
