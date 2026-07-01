from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class SitemapTimeoutUrls(Rule):
    id = "sitemap_timeout_urls"
    name = "Timed Out URLs in Sitemap"
    category = "Sitemaps"
    severity = "warning"
    description = (
        "URLs del sitemap.xml que no respondieron durante el crawl "
        "(timeout / no response, status 0)."
    )
    fix_guidance = (
        "Investiga por quÃ© la URL no responde (servidor lento, firewall, "
        "rate limit). Considera retirarla del sitemap mientras no estÃ© sana."
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
              AND COALESCE(status_code, 0) = 0
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL en sitemap sin respuesta (timeout): {url}",
            )
