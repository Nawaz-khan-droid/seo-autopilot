from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangMissingAnnotations(Rule):
    id = "hreflang_missing_annotations"
    name = "Hreflang Missing Annotations"
    category = "Hreflang"
    severity = "warning"
    enabled_by_default = False  # TODO(schema): heuristic detection of multilingual sites
    description = (
        "PÃ¡ginas que parecen tener equivalentes en otros idiomas pero no "
        "declaran hreflang. DetecciÃ³n heurÃ­stica pendiente."
    )
    fix_guidance = (
        "Si tu sitio tiene versiones en mÃºltiples idiomas, declara hreflang "
        "explÃ­cito en cada URL del cluster (HTML, sitemap o header)."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # TODO(schema): requires multilingual cluster heuristic across URLs
        return iter([])
