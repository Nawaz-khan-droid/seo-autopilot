"""Content semantically similar rule.

# TODO(schema): requires sentence-transformer embeddings (SBERT) not yet
# available in the schema. Skipped for MVP.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ContentSemanticallySimilar(Rule):
    id = "content_semantically_similar"
    name = "Content Semantically Similar"
    category = "Content"
    severity = "info"
    description = "PÃ¡ginas con significado comparable (requiere embeddings semÃ¡nticos)."
    fix_guidance = (
        "Cuando estÃ© disponible: revisa pÃ¡ginas semÃ¡nticamente parecidas y considera "
        "consolidarlas o diferenciarlas con contenido Ãºnico."
    )
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query: needs SBERT embeddings column
        return iter([])
