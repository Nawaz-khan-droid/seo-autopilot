from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class CanonicalLoop(Rule):
    id = "canonical_loop"
    name = "Canonical Loop"
    category = "Canonicals"
    severity = "critical"
    description = "Existe un ciclo en la cadena de canonicals (A -> B -> ... -> A)."
    fix_guidance = (
        "Rompe el ciclo: identifica la URL preferida del grupo y haz que "
        "todas las demÃ¡s apunten a ella, y la preferida se canonicalice "
        "a sÃ­ misma. Los loops invalidan toda la seÃ±al de canonicalizaciÃ³n."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Recursive CTE: walk canonical chain up to 10 hops, flag URLs whose
        # walk lands back on themselves.
        rows = con.execute(
            """
            WITH RECURSIVE chain AS (
                SELECT
                    url_id      AS root_id,
                    url         AS root_url,
                    canonical   AS next_url,
                    1           AS hop
                FROM urls
                WHERE canonical IS NOT NULL
                  AND canonical <> url
                UNION ALL
                SELECT
                    c.root_id,
                    c.root_url,
                    u.canonical,
                    c.hop + 1
                FROM chain c
                JOIN urls u ON u.url = c.next_url
                WHERE c.hop < 10
                  AND u.canonical IS NOT NULL
                  AND u.canonical <> u.url
                  AND u.url <> c.root_url
            )
            SELECT root_id, root_url, hop
            FROM chain
            WHERE next_url = root_url
            """
        ).fetchall()
        seen: set[int] = set()
        for url_id, url, hop in rows:
            if url_id in seen:
                continue
            seen.add(url_id)
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url, "loop_length": hop},
                message=f"Loop de canonicals (longitud {hop}): {url}",
            )
