from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue
from modules.seo_rules.rules.amp._helpers import AMP_URL_SQL


@register_rule
class AmpUrl403(Rule):
    id = "amp_url_403"
    name = "AMP URL is 403"
    category = "AMP"
    severity = "critical"
    description = "PÃ¡gina AMP devuelve 403 Forbidden."
    fix_guidance = (
        "Verifica permisos del servidor o configuraciÃ³n de WAF que bloquea "
        "la pÃ¡gina AMP."
    )
    references = [
        "https://amp.dev/documentation/guides-and-tutorials/start/create/",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            f"""
            SELECT url_id, url
            FROM urls
            WHERE status_code = 403 AND {AMP_URL_SQL}
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "status": 403},
                message=f"AMP {url} devuelve 403",
            )
