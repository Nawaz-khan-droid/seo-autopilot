from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue
from modules.seo_rules.rules.amp._helpers import AMP_URL_SQL


@register_rule
class AmpUrlNoindex(Rule):
    id = "amp_url_noindex"
    name = "AMP URL is Noindex"
    category = "AMP"
    severity = "warning"
    description = "PÃ¡gina AMP marcada noindex."
    fix_guidance = "Retira la directiva noindex; AMP debe ser indexable."
    references = [
        "https://amp.dev/documentation/guides-and-tutorials/start/create/",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            f"""
            SELECT url_id, url
            FROM urls
            WHERE status_code = 200
              AND is_indexable = FALSE
              AND (COALESCE(meta_robots, '') ILIKE '%noindex%'
                   OR COALESCE(x_robots_tag, '') ILIKE '%noindex%')
              AND {AMP_URL_SQL}
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"AMP {url} es noindex",
            )
