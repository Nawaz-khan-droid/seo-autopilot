"""Mobile alternate link (<link rel='alternate' media='only screen and (max-width:...)'>).

# TODO(schema): requires `<link rel='alternate'>` non-hreflang variants.
The `hreflang` table only stores language alternates. Mobile-alternate links
(media-query alternates pointing to m.example.com style mobile sites) aren't
tracked separately.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class MobileAlternateLink(Rule):
    id = "mobile_alternate_link"
    name = "Mobile Alternate Link"
    category = "Mobile"
    severity = "info"
    description = (
        "PÃ¡gina declara <link rel='alternate' media='...'> hacia versiÃ³n mobile. "
        "PatrÃ³n m. legacy: considera adoptar diseÃ±o responsive."
    )
    fix_guidance = (
        "El patrÃ³n m.example.com estÃ¡ deprecado. Migra a un sitio Ãºnico con "
        "diseÃ±o responsive y elimina los links rel=alternate de mobile."
    )
    references = [
        "https://developers.google.com/search/mobile-sites/mobile-seo/separate-urls",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs <link rel=alternate media=> capture
        return iter([])
