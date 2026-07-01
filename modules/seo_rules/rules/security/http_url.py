from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HttpUrl(Rule):
    id = "http_url"
    name = "HTTP URL"
    category = "Security"
    severity = "critical"
    description = "URL servida por HTTP en lugar de HTTPS."
    fix_guidance = (
        "Migra la URL a HTTPS y configura una redirecciÃ³n 301 desde la versiÃ³n HTTP. "
        "AsegÃºrate de que el certificado TLS sea vÃ¡lido y de incluir HSTS."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/Security",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE url LIKE 'http://%'
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL servida por HTTP: {url}",
            )
