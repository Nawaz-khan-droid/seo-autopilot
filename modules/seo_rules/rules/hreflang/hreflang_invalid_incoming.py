from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

_PATTERN = r"^([a-z]{2,3})(-[A-Z]{2})?$"


@register_rule
class HreflangInvalidIncoming(Rule):
    id = "hreflang_invalid_incoming"
    name = "Hreflang Invalid Incoming Annotations"
    category = "Hreflang"
    severity = "critical"
    description = (
        "Una URL recibe hreflang entrantes con cÃ³digos de idioma/regiÃ³n "
        "invÃ¡lidos. Google descartarÃ¡ esas anotaciones."
    )
    fix_guidance = (
        "Audita las URLs origen que enlazan a esta pÃ¡gina vÃ­a hreflang y "
        "corrige los cÃ³digos lang invÃ¡lidos a su forma ISO 639/3166."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            f"""
            SELECT u.url_id, u.url,
                   list(distinct h.lang) AS bad_langs,
                   list(distinct h.source_url_id) AS sources
            FROM urls u
            JOIN hreflang h ON h.href_url_id = u.url_id
            WHERE h.lang IS NULL
               OR (h.lang <> 'x-default' AND NOT regexp_matches(h.lang, '{_PATTERN}'))
            GROUP BY u.url_id, u.url
            """
        ).fetchall()
        for url_id, url, bad_langs, sources in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "invalid_langs": list(bad_langs),
                    "source_count": len(sources),
                },
                message=(
                    f"{url} recibe hreflang con langs invÃ¡lidos: {bad_langs}"
                ),
            )
