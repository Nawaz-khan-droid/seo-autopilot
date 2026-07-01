from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlSessionIdParams(Rule):
    id = "url_session_id_params"
    name = "Session ID parameters"
    category = "URL"
    severity = "warning"
    description = (
        "URL con parÃ¡metros de session ID (`PHPSESSID`, `SID`, `sessionid`, "
        "`jsessionid`, `sid`). Genera URLs Ãºnicas por sesiÃ³n y duplicaciÃ³n."
    )
    fix_guidance = (
        "Mueve la sesiÃ³n a cookies. Si no es posible, configura un parÃ¡metro "
        "URL en Search Console y bloquea con robots.txt o canonical."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Case-insensitive match
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE regexp_matches(
                lower(url),
                '[?&](phpsessid|jsessionid|sessionid|sid|aspsessionid|cfid|cftoken)='
            )
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL con session ID: {url}",
            )
