from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ImageOver100Kb(Rule):
    id = "image_over_100kb"
    name = "Image Over 100 KB"
    category = "Images"
    severity = "info"
    description = "Imagen con peso superior a 100 KB."
    fix_guidance = (
        "Comprime la imagen (mozjpeg/webp/avif), redimensiona a su tamaÃ±o real "
        "de display, o sirve formatos modernos. Objetivo: <100 KB para imÃ¡genes "
        "estÃ¡ndar y <300 KB para hero images cuidadosamente optimizadas."
    )
    references = [
        "https://web.dev/articles/serve-images-webp",
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img",
    ]

    THRESHOLD = 100 * 1024  # 100 KB

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            f"""
            SELECT r.source_url_id, r.resource_url, r.size_bytes, u.url
            FROM resources r
            LEFT JOIN urls u ON u.url_id = r.source_url_id
            WHERE r.resource_type = 'image'
              AND r.size_bytes IS NOT NULL
              AND r.size_bytes > {self.THRESHOLD}
            """
        ).fetchall()
        for source_url_id, resource_url, size_bytes, page_url in rows:
            kb = size_bytes / 1024.0
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "page_url": page_url,
                    "image_url": resource_url,
                    "size_bytes": size_bytes,
                    "size_kb": round(kb, 1),
                },
                message=f"Imagen de {kb:.1f} KB en {page_url}: {resource_url}",
            )
