from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ContentNearDuplicates(Rule):
    id = "content_near_duplicates"
    name = "Content Near Duplicates"
    category = "Content"
    severity = "info"
    description = "MÃºltiples URLs indexables comparten el mismo simhash (contenido sustancialmente similar)."
    fix_guidance = (
        "Diferencia el contenido entre pÃ¡ginas casi idÃ©nticas o consolÃ­dalas con un canonical. "
        "Para MVP usamos coincidencia exacta de simhash; futuras versiones aÃ±adirÃ¡n Hamming distance."
    )
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # MVP: same simhash counts as near-duplicate.
        # TODO(future): implement Hamming distance < threshold across simhashes.
        rows = con.execute(
            """
            WITH dups AS (
                SELECT simhash AS sh,
                       COUNT(*) AS n,
                       list(url_id ORDER BY url_id) AS url_ids,
                       list(url   ORDER BY url_id) AS urls,
                       list(content_hash ORDER BY url_id) AS hashes
                FROM urls
                WHERE simhash IS NOT NULL
                  AND is_indexable = TRUE
                GROUP BY simhash
                HAVING COUNT(*) > 1
            )
            SELECT sh, n, url_ids, urls, hashes FROM dups
            """
        ).fetchall()
        for simhash, n, url_ids, urls, hashes in rows:
            # Skip groups where ALL content_hashes are identical -> handled by exact_duplicates
            distinct_hashes = {h for h in hashes if h is not None}
            if len(distinct_hashes) <= 1 and None not in (hashes or [None]):
                # all hashes equal -> exact dup, skip
                if len(distinct_hashes) == 1:
                    continue
            for uid, u in zip(url_ids, urls):
                yield Issue(
                    rule_id=self.id,
                    url_id=uid,
                    severity=self.severity,
                    category=self.category,
                    evidence={
                        "url": u,
                        "simhash": str(simhash),
                        "near_duplicate_count": n,
                        "shared_with": [x for x in urls if x != u],
                    },
                    message=f"Contenido casi idÃ©ntico (simhash compartido) en {n} URLs: {u}",
                )
