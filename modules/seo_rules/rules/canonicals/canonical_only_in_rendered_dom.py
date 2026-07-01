"""TODO(schema): requires comparison of canonical extracted from raw HTML
vs canonical extracted from rendered DOM."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalOnlyInRenderedDom(Rule):
    id = "canonical_only_in_rendered_dom"
    name = "Canonical Only In Rendered DOM"
    category = "Canonicals"
    severity = "warning"
    description = "Canonical solo aparece tras el render JS, no en HTML estÃ¡tico."
    fix_guidance = (
        "Inyecta el canonical en el HTML servidor. Si solo aparece tras "
        "renderizar JS, Googlebot puede no verlo en el primer pase y la "
        "indexaciÃ³n se retrasa o falla."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.canonical_source vs urls.canonical_rendered.
    requires_rendered_html = True
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
