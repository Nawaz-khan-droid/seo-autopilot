from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HreflangCanonicalizedHasIncoming(Rule):
    id = "hreflang_canonicalized_has_incoming"
    name = "Hreflang to Canonicalized URL (incoming)"
    category = "Hreflang"
    severity = "warning"
    description = (
        "Una URL canonicalizada (canonical != url) recibe anotaciones hreflang "
        "entrantes. Google ignorarÃ¡ el cluster porque la URL no es la canÃ³nica."
    )
    fix_guidance = (
        "Apunta los hreflang entrantes a la URL canÃ³nica del cluster, no a una "
        "URL canonicalizada. Alternativamente, retira el canonical si la URL "
        "debe ser la canÃ³nica del idioma/regiÃ³n."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT DISTINCT u.url_id, u.url, u.canonical
            FROM urls u
            JOIN hreflang h ON h.href_url_id = u.url_id
            WHERE u.canonical IS NOT NULL
              AND u.canonical <> u.url
            """
        ).fetchall()
        for url_id, url, canonical in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "canonical": canonical},
                message=(
                    f"{url} recibe hreflang entrantes pero estÃ¡ canonicalizada a "
                    f"{canonical}"
                ),
            )
