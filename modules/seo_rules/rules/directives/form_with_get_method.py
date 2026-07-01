"""Form With GET Method.

# TODO(schema): requires forms tracking (form action, method) which is not
yet present in the schema. Crawler currently does not extract <form> tags.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class FormWithGetMethod(Rule):
    id = "form_with_get_method"
    name = "Form With GET Method"
    category = "Directives"
    severity = "info"
    description = (
        "PÃ¡gina contiene un `<form method=\"get\">`, lo que puede generar "
        "URLs parametrizadas indexables sin querer."
    )
    fix_guidance = (
        "Considera usar `method=\"post\"` para formularios que no deberÃ­an "
        "ser indexables (bÃºsquedas internas, filtros), o bloquea con robots."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” schema does not yet track forms
        return iter([])
