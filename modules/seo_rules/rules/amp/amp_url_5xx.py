from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue
from modules.seo_rules.rules.amp._helpers import AMP_URL_SQL


@register_rule
class AmpUrl5xx(Rule):
    id = "amp_url_5xx"
    name = "AMP URL is 5XX"
    category = "AMP"
    severity = "critical"
    description = "PÃ¡gina AMP devuelve un error de servidor 5XX."
    fix_guidance = "Investiga la causa del error 5XX en el servidor que sirve AMP."
    references = [
        "https://amp.dev/documentation/guides-and-tutorials/start/create/",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            f"""
            SELECT url_id, url, status_code
            FROM urls
            WHERE status_code BETWEEN 500 AND 599 AND {AMP_URL_SQL}
            """
        ).fetchall()
        for url_id, url, status in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "status": status},
                message=f"AMP {url} devuelve {status}",
            )
