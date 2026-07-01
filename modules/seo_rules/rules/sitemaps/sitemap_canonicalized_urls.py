from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SitemapCanonicalizedUrls(Rule):
    id = "sitemap_canonicalized_urls"
    name = "Canonicalized URLs in Sitemap"
    category = "Sitemaps"
    severity = "warning"
    description = (
        "URLs presentes en el sitemap declaran un canonical apuntando a una "
        "URL distinta. Es seÃ±al mixta para Google."
    )
    fix_guidance = (
        "El sitemap debe contener solo las URLs canÃ³nicas. Si el canonical "
        "es correcto, sustituye la URL en el sitemap por su versiÃ³n canÃ³nica."
    )
    references = [
        "https://www.sitemaps.org/protocol.html",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, canonical
            FROM urls
            WHERE COALESCE(from_sitemap, FALSE) = TRUE
              AND canonical IS NOT NULL
              AND canonical <> ''
              AND canonical <> url
            """
        ).fetchall()
        for url_id, url, canonical in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "canonical": canonical},
                message=f"URL en sitemap con canonical distinto: {url} â†’ {canonical}",
            )
