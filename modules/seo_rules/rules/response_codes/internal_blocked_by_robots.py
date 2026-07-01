from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class InternalBlockedByRobots(Rule):
    id = "internal_blocked_by_robots"
    name = "Blocked by Robots.txt"
    category = "Response Codes"
    severity = "warning"
    description = "URL interna bloqueada por una directiva Disallow en robots.txt."
    fix_guidance = (
        "Revisa si el bloqueo es intencional. Si la URL deberÃ­a indexarse, elimina la "
        "directiva Disallow correspondiente. Si NO deberÃ­a indexarse, mejor combina con "
        "noindex (no solo robots.txt) para evitar que aparezca como 'indexed without content'."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots/intro",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE from_robots = TRUE
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL bloqueada por robots.txt: {url}",
            )
