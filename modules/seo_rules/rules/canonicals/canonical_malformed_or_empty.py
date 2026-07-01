from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalMalformedOrEmpty(Rule):
    id = "canonical_malformed_or_empty"
    name = "Canonical Malformed Or Empty"
    category = "Canonicals"
    severity = "warning"
    description = "Canonical presente pero vacÃ­o o con valor no http(s)."
    fix_guidance = (
        "El href del canonical debe ser una URL absoluta http:// o https:// "
        "bien formada. Corrige el atributo o elimÃ­nalo si era invÃ¡lido."
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
              AND (
                trim(canonical) = ''
                OR canonical NOT LIKE 'http://%'
                AND canonical NOT LIKE 'https://%'
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
                message=f"Canonical mal formado o vacÃ­o: {canonical!r}",
            )
