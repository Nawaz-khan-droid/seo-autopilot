from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class OutlinksToLocalhost(Rule):
    id = "outlinks_to_localhost"
    name = "Outlinks To Localhost"
    category = "Links"
    severity = "critical"
    description = "Links que apuntan a localhost / 127.0.0.1 / ::1 (tÃ­pico fallo de despliegue)."
    fix_guidance = (
        "Reemplaza las URLs localhost por las URLs pÃºblicas del sitio. "
        "Es un fallo comÃºn al copiar HTML desde entornos de desarrollo."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT source_url_id, target_url, anchor
            FROM links
            WHERE target_url LIKE '%localhost%'
               OR target_url LIKE '%127.0.0.1%'
               OR target_url LIKE '%[::1]%'
               OR target_url LIKE '%://::1%'
            """
        ).fetchall()
        for source_url_id, target_url, anchor in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={"target_url": target_url, "anchor": anchor},
                message=f"Outlink a localhost detectado: {target_url}",
            )
