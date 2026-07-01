from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NofollowHtmlVsHeaderMismatch(Rule):
    id = "nofollow_html_vs_header_mismatch"
    name = "Nofollow HTML vs Header Mismatch"
    category = "Directives"
    severity = "warning"
    description = (
        "Inconsistencia: la URL declara `nofollow` solo en uno de los dos "
        "canales (meta robots HTML o X-Robots-Tag), no en ambos."
    )
    fix_guidance = (
        "Si pretendes evitar el seguimiento de enlaces, declara `nofollow` "
        "en ambos canales. Si no, retÃ­ralo de donde sobre."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, meta_robots, x_robots_tag
            FROM urls
            WHERE (
                LOWER(COALESCE(meta_robots, '')) LIKE '%nofollow%'
                AND LOWER(COALESCE(x_robots_tag, '')) NOT LIKE '%nofollow%'
            )
            OR (
                LOWER(COALESCE(meta_robots, '')) NOT LIKE '%nofollow%'
                AND LOWER(COALESCE(x_robots_tag, '')) LIKE '%nofollow%'
            )
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
                    "in_meta": "nofollow" in (meta_robots or "").lower(),
                    "in_header": "nofollow" in (x_robots_tag or "").lower(),
                },
                message=f"Mismatch nofollow (meta vs header) en: {url}",
            )
