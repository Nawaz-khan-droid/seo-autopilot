from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Sitemap5xxUrls(Rule):
    id = "sitemap_5xx_urls"
    name = "5XX URL in Sitemap"
    category = "Sitemaps"
    severity = "critical"
    description = (
        "Una URL del sitemap.xml devuelve un cÃ³digo 5xx (servidor). "
        "Compromete crawl budget y la imagen de salud del sitio."
    )
    fix_guidance = (
        "Investiga la causa del 5xx (errores de aplicaciÃ³n, base de datos, "
        "rate limiting). Mientras tanto, retira la URL del sitemap si no "
        "puedes restaurarla rÃ¡pido."
    )
    references = [
        "https://www.sitemaps.org/protocol.html",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, status_code
            FROM urls
            WHERE COALESCE(from_sitemap, FALSE) = TRUE
              AND status_code BETWEEN 500 AND 599
            """
        ).fetchall()
        for url_id, url, status in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "status_code": status},
                message=f"URL {status} en sitemap: {url}",
            )
