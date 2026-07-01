"""TODO(schema): requires source vs rendered canonical columns."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalRenderVsSourceMismatch(Rule):
    id = "canonical_render_vs_source_mismatch"
    name = "Canonical Render vs Source Mismatch"
    category = "Canonicals"
    severity = "warning"
    description = "El canonical cambia entre el HTML servido y el HTML renderizado."
    fix_guidance = (
        "El canonical no deberÃ­a cambiar al renderizar JS. Si lo hace, "
        "decide cuÃ¡l es la versiÃ³n correcta y servirla siempre desde el "
        "HTML inicial para evitar seÃ±ales contradictorias."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.canonical_source + urls.canonical_rendered columns.
    requires_rendered_html = True
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
