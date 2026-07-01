from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangDisallowedHasIncoming(Rule):
    id = "hreflang_disallowed_has_incoming"
    name = "Hreflang to Disallowed URL (incoming)"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Una URL bloqueada por robots.txt recibe anotaciones hreflang. Google "
        "no podrÃ¡ leer la pÃ¡gina y descartarÃ¡ la relaciÃ³n."
    )
    fix_guidance = (
        "Permite el rastreo de la URL en robots.txt o redirige los hreflang a "
        "una URL accesible del mismo idioma/regiÃ³n."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT DISTINCT u.url_id, u.url
            FROM urls u
            JOIN hreflang h ON h.href_url_id = u.url_id
            WHERE u.from_robots = TRUE
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"{url} estÃ¡ bloqueada por robots.txt pero recibe hreflang entrantes",
            )
