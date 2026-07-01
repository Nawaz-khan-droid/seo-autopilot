"""TODO(schema): requires separate columns for HTML canonical vs HTTP
header `Link: <...>; rel=canonical` value."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalHtmlVsHeaderMismatch(Rule):
    id = "canonical_html_vs_header_mismatch"
    name = "Canonical HTML vs Header Mismatch"
    category = "Canonicals"
    severity = "warning"
    description = "Canonical en HTML difiere del declarado en cabecera HTTP."
    fix_guidance = (
        "Unifica el canonical: el HTML y el header HTTP `Link` deben "
        "apuntar a la misma URL. Cuando difieren, Google puede elegir "
        "cualquiera, lo que es impredecible."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.canonical_header column.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
