from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

DEPTH_THRESHOLD = 6


@register_rule
class PagesHighCrawlDepth(Rule):
    id = "pages_high_crawl_depth"
    name = "Pages At High Crawl Depth"
    category = "Links"
    severity = "info"
    description = (
        f"URL a profundidad de crawl > {DEPTH_THRESHOLD} desde la home. "
        "PÃ¡ginas muy profundas tienen menos crawl frequency."
    )
    fix_guidance = (
        f"Reestructura la navegaciÃ³n interna para que las pÃ¡ginas relevantes "
        f"queden a {DEPTH_THRESHOLD} clicks o menos desde la home."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, depth
            FROM urls
            WHERE depth IS NOT NULL
              AND depth > ?
            """,
            [DEPTH_THRESHOLD],
        ).fetchall()
        for url_id, url, depth in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "depth": depth,
                    "threshold": DEPTH_THRESHOLD,
                },
                message=f"URL a profundidad {depth} (>{DEPTH_THRESHOLD}): {url}",
            )
