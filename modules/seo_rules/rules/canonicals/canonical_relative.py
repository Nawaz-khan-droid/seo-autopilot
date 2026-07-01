"""TODO(schema): requires raw `<link rel=canonical href>` value before URL
canonicalisation. The current schema stores the canonical already resolved
to absolute, so we cannot detect relative hrefs (e.g. `/foo`) post-hoc."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalRelative(Rule):
    id = "canonical_relative"
    name = "Canonical Is Relative"
    category = "Canonicals"
    severity = "info"
    description = "Canonical declarado con URL relativa en lugar de absoluta."
    fix_guidance = (
        "Usa siempre URLs absolutas (con esquema y dominio) en el "
        "atributo href del canonical. Las URLs relativas son ambiguas "
        "y pueden ser resueltas de forma incorrecta por crawlers."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs raw canonical href (pre-resolution) column.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” cannot detect relative canonicals with current schema
        return iter([])
