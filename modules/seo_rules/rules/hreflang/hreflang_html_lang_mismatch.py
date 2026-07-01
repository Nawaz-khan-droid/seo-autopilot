from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangHtmlLangMismatch(Rule):
    id = "hreflang_html_lang_mismatch"
    name = "Hreflang and HTML lang mismatch"
    category = "Hreflang"
    severity = "warning"
    description = (
        "La auto-referencia hreflang declara un idioma distinto al del "
        "atributo lang del HTML. Inconsistencia que confunde a buscadores."
    )
    fix_guidance = (
        "Alinea el cÃ³digo de idioma del <html lang> con el lang declarado "
        "en la auto-referencia hreflang (la entrada hreflang cuyo href "
        "apunta a la propia URL)."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT u.url_id, u.url, u.lang AS html_lang, h.lang AS hreflang_lang
            FROM urls u
            JOIN hreflang h
              ON h.source_url_id = u.url_id
             AND h.href_url_id  = u.url_id
            WHERE u.lang IS NOT NULL
              AND trim(u.lang) <> ''
              AND h.lang <> 'x-default'
              AND lower(split_part(h.lang, '-', 1)) <> lower(split_part(u.lang, '-', 1))
            """
        ).fetchall()
        for url_id, url, html_lang, hreflang_lang in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "html_lang": html_lang,
                    "hreflang_lang": hreflang_lang,
                },
                message=(
                    f"{url} tiene <html lang={html_lang!r}> pero la auto-referencia "
                    f"hreflang declara lang={hreflang_lang!r}"
                ),
            )
