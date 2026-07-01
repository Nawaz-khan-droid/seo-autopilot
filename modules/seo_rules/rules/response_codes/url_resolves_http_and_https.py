from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlResolvesHttpAndHttps(Rule):
    id = "url_resolves_http_and_https"
    name = "URL resolves under HTTP and HTTPS"
    category = "Response Codes"
    severity = "critical"
    description = (
        "Existe versiÃ³n HTTP y HTTPS de la misma URL y ambas devuelven 200 â€” duplicado masivo."
    )
    fix_guidance = (
        "El sitio debe servirse exclusivamente por HTTPS. Configura un 301 permanente "
        "de toda URL HTTP a su equivalente HTTPS y aÃ±ade HSTS para forzar el upgrade en clientes."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Para cada URL HTTPS con 200, busca su gemela HTTP tambiÃ©n 200.
        # Reportamos ambas (la HTTP y la HTTPS) para que el cliente las vea.
        rows = con.execute(
            """
            WITH pairs AS (
                SELECT
                    https_u.url_id    AS https_url_id,
                    https_u.url       AS https_url,
                    http_u.url_id     AS http_url_id,
                    http_u.url        AS http_url
                FROM urls https_u
                JOIN urls http_u
                  ON http_u.url = 'http://'  || substr(https_u.url, 9)
                 AND https_u.url LIKE 'https://%'
                WHERE https_u.status_code = 200
                  AND http_u.status_code = 200
            )
            SELECT https_url_id, https_url, http_url_id, http_url FROM pairs
            """
        ).fetchall()
        for https_url_id, https_url, http_url_id, http_url in rows:
            # emit one issue per side so both URLs surface in reports
            yield Issue(
                rule_id=self.id,
                url_id=https_url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": https_url, "twin": http_url, "scheme": "https"},
                message=f"URL accesible por HTTP y HTTPS: {https_url}",
            )
            yield Issue(
                rule_id=self.id,
                url_id=http_url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": http_url, "twin": https_url, "scheme": "http"},
                message=f"URL accesible por HTTP y HTTPS: {http_url}",
            )
