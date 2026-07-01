from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SitemapDisallowedUrls(Rule):
    id = "sitemap_disallowed_urls"
    name = "Disallowed URLs in Sitemap"
    category = "Sitemaps"
    severity = "warning"
    description = (
        "URLs presentes en el sitemap estÃ¡n bloqueadas por robots.txt. "
        "Google no podrÃ¡ rastrearlas a pesar de aparecer en el sitemap."
    )
    fix_guidance = (
        "Decide la intenciÃ³n real: si la URL debe indexarse, retira la regla "
        "Disallow de robots.txt; si debe bloquearse, retÃ­rala del sitemap."
    )
    references = [
        "https://www.sitemaps.org/protocol.html",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE COALESCE(from_sitemap, FALSE) = TRUE
              AND COALESCE(from_robots, FALSE) = TRUE
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL en sitemap bloqueada por robots.txt: {url}",
            )
