"""TODO(schema): requires list of all canonical values found in the HTML
to detect conflicting ones. The current schema persists a single value."""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalMultipleConflicting(Rule):
    id = "canonical_multiple_conflicting"
    name = "Canonical Multiple Conflicting"
    category = "Canonicals"
    severity = "critical"
    description = "MÃºltiples canonicals en la misma pÃ¡gina apuntando a URLs distintas."
    fix_guidance = (
        "Deja un Ãºnico canonical apuntando a la URL preferida. MÃºltiples "
        "canonicals con destinos distintos invalidan toda la seÃ±al."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]
    # TODO(schema): needs urls.canonicals_all VARCHAR[] column.
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        return iter([])
