from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ImageMissingAltAttribute(Rule):
    id = "image_missing_alt_attribute"
    name = "Image Missing Alt Attribute"
    category = "Images"
    severity = "warning"
    description = "Imagen no tiene atributo alt (NULL), no solo vacÃ­o."
    fix_guidance = (
        "AÃ±ade siempre el atributo alt a toda imagen <img>. Si es decorativa, "
        "dÃ©jalo vacÃ­o (alt=''). Si es informativa, descrÃ­bela. La ausencia "
        "completa del atributo perjudica accesibilidad y SEO de imagen."
    )
    references = [
        "https://web.dev/articles/serve-images-webp",
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT r.source_url_id, r.resource_url, u.url
            FROM resources r
            LEFT JOIN urls u ON u.url_id = r.source_url_id
            WHERE r.resource_type = 'image'
              AND r.alt IS NULL
            """
        ).fetchall()
        for source_url_id, resource_url, page_url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={"page_url": page_url, "image_url": resource_url},
                message=f"Imagen sin atributo alt en {page_url}: {resource_url}",
            )
