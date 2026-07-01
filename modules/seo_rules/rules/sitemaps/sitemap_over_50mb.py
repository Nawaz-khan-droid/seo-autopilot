"""Sitemap Over 50MB.

# TODO(schema): requires sitemap-level file size metadata.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SitemapOver50Mb(Rule):
    id = "sitemap_over_50mb"
    name = "XML Sitemap Over 50MB"
    category = "Sitemaps"
    severity = "warning"
    description = (
        "Un sitemap.xml supera los 50 MB descomprimidos, el lÃ­mite del "
        "protocolo de sitemaps."
    )
    fix_guidance = (
        "Divide el sitemap en archivos < 50 MB y comprÃ­melos con gzip "
        "(.xml.gz) si es posible."
    )
    references = [
        "https://www.sitemaps.org/protocol.html",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” sitemap file size not in schema
        return iter([])
