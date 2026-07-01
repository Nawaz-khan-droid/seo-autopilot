from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalToExternal(Rule):
    id = "canonical_to_external"
    name = "Canonical Points To External"
    category = "Canonicals"
    severity = "info"
    description = "El canonical apunta a un dominio externo."
    fix_guidance = (
        "Si la canonicalizaciÃ³n cross-domain es intencional (sindicaciÃ³n, "
        "mirror oficial) no requiere acciÃ³n. Si no, apunta el canonical "
        "a una URL del mismo dominio: cualquier otra cosa puede ceder "
        "seÃ±ales SEO al externo."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            r"""
            SELECT url_id, url, canonical,
                   regexp_extract(url,       '^https?://([^/]+)', 1) AS host_url,
                   regexp_extract(canonical, '^https?://([^/]+)', 1) AS host_canon
            FROM urls
            WHERE canonical IS NOT NULL
              AND canonical LIKE 'http%'
              AND regexp_extract(url,       '^https?://([^/]+)', 1) <> ''
              AND regexp_extract(canonical, '^https?://([^/]+)', 1) <> ''
              AND regexp_extract(url,       '^https?://([^/]+)', 1)
                 <> regexp_extract(canonical, '^https?://([^/]+)', 1)
            """
        ).fetchall()
        for url_id, url, canonical, host_url, host_canon in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "canonical": canonical,
                    "host_url": host_url,
                    "host_canonical": host_canon,
                },
                message=f"Canonical externo: {canonical}",
            )
