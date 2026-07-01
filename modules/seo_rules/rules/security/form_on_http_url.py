"""Form on HTTP URL.

# TODO(schema): requires form-action extraction (no `forms` table or
# action column on `links` yet).
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class FormOnHttpUrl(Rule):
    id = "form_on_http_url"
    name = "Form on HTTP URL"
    category = "Security"
    severity = "critical"
    description = "PÃ¡gina HTTP que contiene un formulario (toda la submission viaja en claro)."
    fix_guidance = (
        "Migra la pÃ¡gina a HTTPS o, como mÃ­nimo, pon el formulario en una URL HTTPS. "
        "Los navegadores marcan estos formularios como 'No seguro'."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/Security",
    ]
    enabled_by_default = False  # awaiting schema column for form actions

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs form extraction
        return iter([])
