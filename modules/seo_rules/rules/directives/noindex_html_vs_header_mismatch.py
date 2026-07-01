from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class NoindexHtmlVsHeaderMismatch(Rule):
    id = "noindex_html_vs_header_mismatch"
    name = "Noindex HTML vs Header Mismatch"
    category = "Directives"
    severity = "warning"
    description = (
        "Inconsistencia: la URL declara `noindex` solo en uno de los dos "
        "canales (meta robots HTML o X-Robots-Tag), no en ambos."
    )
    fix_guidance = (
        "Decide si la pÃ¡gina debe ser indexable o no, y aplica la directiva "
        "de forma coherente. Una declaraciÃ³n en cualquiera de los dos canales "
        "es suficiente para deindexar â€” la inconsistencia confunde auditorÃ­as."
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
                LOWER(COALESCE(meta_robots, '')) LIKE '%noindex%'
                AND LOWER(COALESCE(x_robots_tag, '')) NOT LIKE '%noindex%'
            )
            OR (
                LOWER(COALESCE(meta_robots, '')) NOT LIKE '%noindex%'
                AND LOWER(COALESCE(x_robots_tag, '')) LIKE '%noindex%'
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
                    "in_meta": "noindex" in (meta_robots or "").lower(),
                    "in_header": "noindex" in (x_robots_tag or "").lower(),
                },
                message=f"Mismatch noindex (meta vs header) en: {url}",
            )
