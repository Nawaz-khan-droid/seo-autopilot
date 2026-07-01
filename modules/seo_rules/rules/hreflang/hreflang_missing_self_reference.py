from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangMissingSelfReference(Rule):
    id = "hreflang_missing_self_reference"
    name = "Hreflang Missing Self Reference"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Una pÃ¡gina con anotaciones hreflang no incluye una entrada que "
        "apunte a sÃ­ misma (self-reference)."
    )
    fix_guidance = (
        "AÃ±ade una entrada hreflang adicional para la propia URL, indicando "
        "su lang. Cada cluster hreflang debe contener una self-reference por "
        "cada miembro."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id, u.url
            FROM urls u
            WHERE EXISTS (
                SELECT 1 FROM hreflang h WHERE h.source_url_id = u.url_id
            )
            AND NOT EXISTS (
                SELECT 1 FROM hreflang h
                WHERE h.source_url_id = u.url_id
                  AND (h.href_url_id = u.url_id OR h.href = u.url)
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
                message=f"{url} declara hreflang pero no incluye self-reference",
            )
