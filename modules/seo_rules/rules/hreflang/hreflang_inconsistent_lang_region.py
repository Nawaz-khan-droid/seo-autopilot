from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangInconsistentLangRegion(Rule):
    id = "hreflang_inconsistent_lang_region"
    name = "Hreflang Inconsistent Lang/Region"
    category = "Hreflang"
    severity = "critical"
    description = (
        "El return link existe pero la lang declarada no coincide entre las "
        "dos pÃ¡ginas."
    )
    fix_guidance = (
        "Asegura que cuando A declara B con lang=X, B declare A con lang=Y "
        "consistente. Las inconsistencias rompen el cluster hreflang."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT a.source_url_id,
                   src.url AS source_url,
                   a.lang AS a_lang,
                   a.href,
                   list(DISTINCT b.lang) AS b_langs
            FROM hreflang a
            JOIN hreflang b
              ON b.source_url_id = a.href_url_id
             AND b.href_url_id  = a.source_url_id
            LEFT JOIN urls src ON src.url_id = a.source_url_id
            WHERE a.href_url_id IS NOT NULL
              AND a.source_url_id <> a.href_url_id
            GROUP BY a.source_url_id, src.url, a.lang, a.href
            HAVING NOT list_contains(list(DISTINCT b.lang), a.lang)
            """
        ).fetchall()
        for source_url_id, source_url, a_lang, href, b_langs in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "source_url": source_url,
                    "declared_lang": a_lang,
                    "target": href,
                    "return_langs": list(b_langs) if b_langs else [],
                },
                message=(
                    f"{source_url} declara lang={a_lang!r} hacia {href} pero "
                    f"el return link declara lang={list(b_langs)!r}"
                ),
            )
