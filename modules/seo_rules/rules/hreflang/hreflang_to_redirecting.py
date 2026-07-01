from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangToRedirecting(Rule):
    id = "hreflang_to_redirecting"
    name = "Hreflang to Redirecting URL"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Hreflang apunta a una URL que redirige (3xx o redirect_count > 0)."
    )
    fix_guidance = (
        "Apunta el hreflang al destino final tras seguir todos los redirects "
        "para que Google evalÃºe el cluster sobre URLs estables."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT h.source_url_id,
                   src.url AS source_url,
                   h.lang,
                   h.href,
                   tgt.status_code,
                   tgt.redirect_count
            FROM hreflang h
            JOIN urls tgt ON tgt.url_id = h.href_url_id
            LEFT JOIN urls src ON src.url_id = h.source_url_id
            WHERE h.href_url_id IS NOT NULL
              AND (
                  COALESCE(tgt.redirect_count, 0) > 0
                  OR (tgt.status_code BETWEEN 300 AND 399)
              )
            """
        ).fetchall()
        for source_url_id, source_url, lang, href, status_code, redirect_count in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "lang": lang,
                    "href": href,
                    "status_code": status_code,
                    "redirect_count": redirect_count,
                },
                message=(
                    f"Hreflang lang={lang!r} apunta a {href}, que redirige "
                    f"(status={status_code}, hops={redirect_count})"
                ),
            )
