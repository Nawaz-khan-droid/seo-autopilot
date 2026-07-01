from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangWithoutHtmlLang(Rule):
    id = "hreflang_without_html_lang"
    name = "Hreflang annotations without HTML lang"
    category = "Hreflang"
    severity = "info"
    description = (
        "La pÃ¡gina declara hreflang pero el elemento <html> no tiene atributo "
        "lang. Inconsistencia menor que conviene corregir."
    )
    fix_guidance = (
        "AÃ±ade lang al elemento <html> con el cÃ³digo que corresponda a la "
        "auto-referencia hreflang de esta pÃ¡gina."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT DISTINCT u.url_id, u.url
            FROM urls u
            JOIN hreflang h ON h.source_url_id = u.url_id
            WHERE u.status_code = 200
              AND (u.lang IS NULL OR trim(u.lang) = '')
            """
        ).fetchall()
        for url_id, url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"{url} declara hreflang sin <html lang>",
            )
