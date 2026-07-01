from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlInternalSearch(Rule):
    id = "url_internal_search"
    name = "Internal Search"
    category = "URL"
    severity = "info"
    description = (
        "URL parece corresponder a una pÃ¡gina de bÃºsqueda interna "
        "(`?q=`, `?s=`, `?search=`, `?query=`)."
    )
    fix_guidance = (
        "Las pÃ¡ginas de bÃºsqueda interna no deberÃ­an indexarse. Bloquea con "
        "`Disallow: /?s=` en robots.txt o devuelve `noindex` en estas URLs."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE regexp_matches(url, '[?&](q|s|search|query)=')
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL de bÃºsqueda interna: {url}",
            )
