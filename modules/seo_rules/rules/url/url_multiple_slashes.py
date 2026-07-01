from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlMultipleSlashes(Rule):
    id = "url_multiple_slashes"
    name = "Multiple Slashes"
    category = "URL"
    severity = "warning"
    description = "URL con `//` consecutivos en el path (despuÃ©s del scheme)."
    fix_guidance = (
        "Normaliza el path para eliminar slashes duplicados. Configura el "
        "servidor para 301 a la versiÃ³n limpia y unifica las URLs internas."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Quitar el `//` del scheme: `https://` â†’ marcador y luego buscar `//`.
        # En DuckDB usamos regex. PatrÃ³n: a partir del primer `/` simple del path,
        # detectar `//+`. Tomamos url tras eliminar `https?://` con regexp_replace
        # y comprobamos si contiene `//`.
        rows = con.execute(
            """
            SELECT url_id, url
            FROM urls
            WHERE regexp_matches(
                regexp_replace(url, '^https?://', ''),
                '//'
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
                message=f"URL con slashes consecutivos: {url}",
            )
