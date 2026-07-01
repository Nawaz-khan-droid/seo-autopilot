from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalToDifferentInternal(Rule):
    id = "canonical_to_different_internal"
    name = "Canonical To Different Internal"
    category = "Canonicals"
    severity = "info"
    description = "El canonical apunta a otra URL interna distinta de sÃ­ misma."
    fix_guidance = (
        "Verifica que la canonicalizaciÃ³n es intencional: la URL canÃ³nica "
        "interna deberÃ­a ser la versiÃ³n preferida del contenido. Si no es "
        "asÃ­, apunta el canonical a sÃ­ misma."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            r"""
            SELECT url_id, url, canonical
            FROM urls
            WHERE canonical IS NOT NULL
              AND canonical LIKE 'http%'
              AND canonical <> url
              AND regexp_extract(url,       '^https?://([^/]+)', 1) <> ''
              AND regexp_extract(url,       '^https?://([^/]+)', 1)
                = regexp_extract(canonical, '^https?://([^/]+)', 1)
            """
        ).fetchall()
        for url_id, url, canonical in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "canonical": canonical},
                message=f"Canonical interno distinto: {canonical}",
            )
