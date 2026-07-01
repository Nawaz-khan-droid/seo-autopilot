from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalUnlinked(Rule):
    id = "canonical_unlinked"
    name = "Canonical Unlinked"
    category = "Canonicals"
    severity = "warning"
    description = "El canonical apunta a una URL que no recibe enlaces internos."
    fix_guidance = (
        "Si la URL canÃ³nica es realmente la versiÃ³n preferida, deberÃ­a "
        "estar enlazada desde otras pÃ¡ginas del sitio. AÃ±ade enlaces "
        "internos hacia el canonical o reconsidera la canonicalizaciÃ³n."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Cross-URL: canonical points to a URL that has no entry in links.target_url
        rows = con.execute(
            """
            SELECT a.url_id, a.url, a.canonical
            FROM urls a
            WHERE a.canonical IS NOT NULL
              AND a.canonical <> a.url
              AND a.canonical LIKE 'http%'
              AND NOT EXISTS (
                  SELECT 1 FROM links l WHERE l.target_url = a.canonical
              )
            """
        ).fetchall()
        for url_id, url, canonical in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "canonical": canonical},
                message=f"Canonical sin enlaces internos: {canonical}",
            )
