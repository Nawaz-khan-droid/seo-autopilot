from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class ImageAltOver100Chars(Rule):
    id = "image_alt_over_100_chars"
    name = "Image Alt Text Over 100 Characters"
    category = "Images"
    severity = "info"
    description = "Atributo alt con mÃ¡s de 100 caracteres."
    fix_guidance = (
        "Reduce el alt a una descripciÃ³n breve (â‰¤100 caracteres). Si el contexto "
        "necesita mÃ¡s detalle, usa <figcaption> o un pÃ¡rrafo cercano y deja el "
        "alt como resumen funcional."
    )
    references = [
        "https://web.dev/articles/serve-images-webp",
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img",
    ]

    THRESHOLD = 100

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            f"""
            SELECT r.source_url_id, r.resource_url, r.alt, u.url
            FROM resources r
            LEFT JOIN urls u ON u.url_id = r.source_url_id
            WHERE r.resource_type = 'image'
              AND r.alt IS NOT NULL
              AND length(r.alt) > {self.THRESHOLD}
            """
        ).fetchall()
        for source_url_id, resource_url, alt, page_url in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "page_url": page_url,
                    "image_url": resource_url,
                    "alt_length": len(alt),
                    "alt_preview": alt[:120],
                },
                message=(
                    f"Alt de {len(alt)} caracteres en {page_url}: {resource_url}"
                ),
            )
