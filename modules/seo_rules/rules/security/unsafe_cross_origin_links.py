from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UnsafeCrossOriginLinks(Rule):
    id = "unsafe_cross_origin_links"
    name = "Unsafe Cross Origin Links"
    category = "Security"
    severity = "info"
    description = (
        "Enlace externo `target=_blank` sin `rel=\"noopener\"` ni `rel=\"noreferrer\"`. "
        "El destino puede acceder a `window.opener` (tabnabbing)."
    )
    fix_guidance = (
        "AÃ±ade `rel=\"noopener noreferrer\"` a los `<a target=_blank>` que "
        "apuntan a orÃ­genes externos."
    )
    references = [
        "https://web.dev/external-anchors-use-rel-noopener/",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # External link = target_url_id IS NULL (host distinto, no crawleado)
        # AND target_url empieza por http(s):// (descartar mailto:, tel:, etc.)
        # AND rel no contiene noopener/noreferrer.
        rows = con.execute(
            """
            SELECT l.source_url_id,
                   u.url AS source_url,
                   list(l.target_url) AS targets,
                   list(COALESCE(l.rel, '')) AS rels
            FROM links l
            JOIN urls u ON u.url_id = l.source_url_id
            WHERE l.target_url_id IS NULL
              AND (l.target_url LIKE 'http://%' OR l.target_url LIKE 'https://%')
              AND COALESCE(l.link_type, 'a') = 'a'
              AND lower(COALESCE(l.rel, '')) NOT LIKE '%noopener%'
              AND lower(COALESCE(l.rel, '')) NOT LIKE '%noreferrer%'
            GROUP BY l.source_url_id, u.url
            """
        ).fetchall()
        for source_url_id, source_url, targets, rels in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": source_url,
                    "unsafe_targets": list(targets),
                    "rels": list(rels),
                    "count": len(targets),
                },
                message=(
                    f"{source_url} tiene {len(targets)} enlace(s) externo(s) "
                    f"sin rel=noopener/noreferrer."
                ),
            )
