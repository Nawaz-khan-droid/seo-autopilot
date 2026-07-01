from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Sitemap3xxUrls(Rule):
    id = "sitemap_3xx_urls"
    name = "3XX URL in Sitemap"
    category = "Sitemaps"
    severity = "warning"
    description = (
        "Una URL del sitemap.xml redirige a otra. El sitemap debe listar "
        "URLs finales (200), no la versiÃ³n que redirecciona."
    )
    fix_guidance = (
        "Sustituye en el sitemap la URL antigua por la URL final tras la "
        "redirecciÃ³n."
    )
    references = [
        "https://www.sitemaps.org/protocol.html",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, redirect_count, final_url, status_code
            FROM urls
            WHERE COALESCE(from_sitemap, FALSE) = TRUE
              AND COALESCE(redirect_count, 0) > 0
            """
        ).fetchall()
        for url_id, url, redirect_count, final_url, status in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "redirect_count": redirect_count,
                    "final_url": final_url,
                    "status_code": status,
                },
                message=f"URL en sitemap redirige ({redirect_count} saltos): {url}",
            )
