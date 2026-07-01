from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalToHttps(Rule):
    id = "canonical_to_https"
    name = "Canonical Points To HTTPS"
    category = "Canonicals"
    severity = "info"
    description = "PÃ¡gina HTTP con canonical apuntando a la versiÃ³n HTTPS."
    fix_guidance = (
        "Es la direcciÃ³n correcta de canonicalizaciÃ³n (HTTP -> HTTPS), "
        "pero idealmente la versiÃ³n HTTP deberÃ­a redirigir 301 a HTTPS "
        "en lugar de servirse con un canonical. Considera implementar "
        "una redirecciÃ³n permanente."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, canonical
            FROM urls
            WHERE canonical IS NOT NULL
              AND canonical LIKE 'https://%'
              AND url LIKE 'http://%'
            """
        ).fetchall()
        for url_id, url, canonical in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "canonical": canonical},
                message=f"Canonical HTTP -> HTTPS: {canonical}",
            )
