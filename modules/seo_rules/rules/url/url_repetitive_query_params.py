from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlRepetitiveQueryParams(Rule):
    id = "url_repetitive_query_params"
    name = "Repetitive query parameters"
    category = "URL"
    severity = "info"
    description = (
        "Mismo nombre de parÃ¡metro aparece 2 o mÃ¡s veces en la query string "
        "(ej. `?color=red&color=blue`). Comportamiento ambiguo segÃºn servidor."
    )
    fix_guidance = (
        "Consolida los valores en un Ãºnico parÃ¡metro (CSV o array sintaxis "
        "segÃºn convenciÃ³n del backend)."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE position('?' IN url) > 0
            """
        ).fetchall()
        for url_id, url in rows:
            qs = url.split("?", 1)[1].split("#", 1)[0]
            keys: list[str] = []
            for pair in qs.split("&"):
                if not pair:
                    continue
                key = pair.split("=", 1)[0]
                if key:
                    keys.append(key)
            seen: dict[str, int] = {}
            for k in keys:
                seen[k] = seen.get(k, 0) + 1
            duplicates = {k: c for k, c in seen.items() if c > 1}
            if not duplicates:
                continue
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "duplicate_params": duplicates},
                message=(
                    f"URL con parÃ¡metros repetidos {list(duplicates)}: {url}"
                ),
            )
