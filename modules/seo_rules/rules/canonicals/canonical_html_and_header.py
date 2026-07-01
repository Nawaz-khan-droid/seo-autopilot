"""TODO(schema): requires separate columns for HTML canonical vs HTTP
header `Link: <...>; rel=canonical` value."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalHtmlAndHeader(Rule):
    id = "canonical_html_and_header"
    name = "Canonical In HTML And Header"
    category = "Canonicals"
    severity = "info"
    description = "Canonical declarado a la vez en HTML y en cabecera HTTP."
    fix_guidance = (
        "Declara el canonical en un Ãºnico sitio (HTML o cabecera HTTP), "
        "no en ambos. Aunque coincidan, duplicar la seÃ±al es ruido."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.canonical_header column.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
