from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HtmlOver2Mb(Rule):
    id = "html_over_2mb"
    name = "HTML Over 2MB"
    category = "Directives"
    severity = "critical"
    description = (
        "El HTML servido supera los 2 MB. Googlebot puede truncar el "
        "contenido a partir de ~2.5 MB y no procesar directivas, schema o "
        "contenido por debajo del corte."
    )
    fix_guidance = (
        "Reduce el peso del HTML inline: minifica, mueve CSS/JS a archivos "
        "externos, elimina contenido oculto y plantillas excesivas. Objetivo "
        "razonable: < 500 KB de HTML."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, content_length
            FROM urls
            WHERE content_length IS NOT NULL
              AND content_length > 2 * 1024 * 1024
              AND COALESCE(content_type, '') LIKE 'text/html%'
            """
        ).fetchall()
        for url_id, url, content_length in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "content_length_bytes": content_length,
                    "content_length_mb": round(content_length / (1024 * 1024), 2),
                },
                message=(
                    f"HTML > 2 MB ({content_length / 1024 / 1024:.2f} MB): {url}"
                ),
            )
