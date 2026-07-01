from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NoindexHtmlAndHeader(Rule):
    id = "noindex_html_and_header"
    name = "Noindex In HTML And Header"
    category = "Directives"
    severity = "info"
    description = (
        "URL declara `noindex` redundantemente en meta robots HTML y en el "
        "header X-Robots-Tag. No es un problema, pero sÃ­ informaciÃ³n Ãºtil."
    )
    fix_guidance = (
        "Una sola declaraciÃ³n basta. Mantenerla duplicada no causa daÃ±o, "
        "pero simplifica la configuraciÃ³n dejarla en un Ãºnico canal."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE LOWER(COALESCE(meta_robots, '')) LIKE '%noindex%'
              AND LOWER(COALESCE(x_robots_tag, '')) LIKE '%noindex%'
            """
        ).fetchall()
        for url_id, url, meta_robots, x_robots_tag in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "meta_robots": meta_robots,
                    "x_robots_tag": x_robots_tag,
                },
                message=f"noindex declarado en HTML y header (redundante): {url}",
            )
