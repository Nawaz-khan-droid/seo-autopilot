from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class Sitemap403Urls(Rule):
    id = "sitemap_403_urls"
    name = "403 URL in Sitemap"
    category = "Sitemaps"
    severity = "warning"
    description = (
        "Una URL del sitemap.xml devuelve 403 Forbidden, lo que puede indicar "
        "configuraciÃ³n de seguridad bloqueando a Googlebot o a tu crawler."
    )
    fix_guidance = (
        "Comprueba si la URL deberÃ­a ser pÃºblica (entonces revisa permisos, "
        "WAF o reglas .htaccess) o si debe retirarse del sitemap."
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
              AND status_code = 403
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "status_code": 403},
                message=f"URL 403 Forbidden en sitemap: {url}",
            )
