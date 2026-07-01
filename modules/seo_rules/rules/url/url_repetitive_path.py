from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlRepetitivePath(Rule):
    id = "url_repetitive_path"
    name = "Repetitive Path"
    category = "URL"
    severity = "info"
    description = (
        "Mismo segmento de path aparece dos o mÃ¡s veces consecutivos "
        "(ej. `/blog/blog/post`)."
    )
    fix_guidance = (
        "Revisa la generaciÃ³n de URLs para evitar concatenaciones errÃ³neas. "
        "Configura redirects 301 a la versiÃ³n correcta."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # DuckDB's regex (RE2) doesn't support backreferences, so we filter in
        # Python: strip scheme+host, split path, look for two consecutive equal
        # segments.
        rows = con.execute("SELECT url_id, url FROM urls").fetchall()
        for url_id, url in rows:
            # quitar `scheme://host`
            after_scheme = url.split("://", 1)[-1]
            path_and_rest = after_scheme.split("/", 1)
            if len(path_and_rest) < 2:
                continue
            path = "/" + path_and_rest[1]
            path = path.split("?", 1)[0].split("#", 1)[0]
            segments = [s for s in path.split("/") if s]
            repeated = None
            for prev, cur in zip(segments, segments[1:]):
                if prev == cur:
                    repeated = cur
                    break
            if repeated is None:
                continue
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "repeated_segment": repeated},
                message=(
                    f"URL con segmento repetido {repeated!r}: {url}"
                ),
            )
