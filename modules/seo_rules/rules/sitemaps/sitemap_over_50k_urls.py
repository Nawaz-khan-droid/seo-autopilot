"""Sitemap Over 50k URLs.

# TODO(schema): requires sitemap-level metadata (e.g. a `sitemaps` table
with `urls_count` per sitemap file). Currently we only mark per-URL
`from_sitemap` boolean.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SitemapOver50kUrls(Rule):
    id = "sitemap_over_50k_urls"
    name = "XML Sitemap Over 50k URLs"
    category = "Sitemaps"
    severity = "warning"
    description = (
        "Un archivo sitemap.xml supera el lÃ­mite de 50.000 URLs definido por "
        "el protocolo de sitemaps."
    )
    fix_guidance = (
        "Divide el sitemap en varios archivos < 50.000 URLs cada uno y "
        "agrupa con un sitemap index."
    )
    references = [
        "https://www.sitemaps.org/protocol.html",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” sitemap-level metadata not yet in schema
        return iter([])
