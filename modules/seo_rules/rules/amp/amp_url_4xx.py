from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue
from modules.seo_rules.rules.amp._helpers import AMP_URL_SQL


@register_rule
class AmpUrl4xx(Rule):
    id = "amp_url_4xx"
    name = "AMP URL is 4XX"
    category = "AMP"
    severity = "critical"
    description = "PÃ¡gina AMP devuelve un error 4XX."
    fix_guidance = (
        "Restaura la pÃ¡gina AMP o retira la referencia amphtml de la pÃ¡gina "
        "non-AMP correspondiente."
    )
    references = [
        "https://amp.dev/documentation/guides-and-tutorials/start/create/",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            f"""
            SELECT url_id, url, status_code
            FROM urls
            WHERE status_code BETWEEN 400 AND 499
              AND status_code <> 403
              AND {AMP_URL_SQL}
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
