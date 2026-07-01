from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ImageMissingSizeAttrs(Rule):
    id = "image_missing_size_attrs"
    name = "Image Missing Size Attributes"
    category = "Images"
    severity = "info"
    description = "Imagen sin atributos width y/o height en el HTML."
    fix_guidance = (
        "AÃ±ade width y height al <img> con la proporciÃ³n real (px o unidades). "
        "Esto reserva espacio en el layout y reduce CLS (Cumulative Layout Shift), "
        "uno de los Core Web Vitals."
    )
    references = [
        "https://web.dev/optimize-cls/#images-without-dimensions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT r.source_url_id, r.resource_url, r.width, r.height, u.url
            FROM resources r
            LEFT JOIN urls u ON u.url_id = r.source_url_id
            WHERE r.resource_type = 'image'
              AND (r.width IS NULL OR r.height IS NULL)
            """
        ).fetchall()
        for source_url_id, resource_url, width, height, page_url in rows:
            missing = []
            if width is None:
                missing.append("width")
            if height is None:
                missing.append("height")
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "page_url": page_url,
                    "image_url": resource_url,
                    "missing_attrs": missing,
                },
                message=(
                    f"Imagen sin {'/'.join(missing)} en {page_url}: {resource_url}"
                ),
            )
