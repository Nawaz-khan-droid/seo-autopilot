from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UrlNonAscii(Rule):
    id = "url_non_ascii"
    name = "Non ASCII Characters"
    category = "URL"
    severity = "info"
    description = "URL contiene caracteres no-ASCII (>= 0x80) sin codificar."
    fix_guidance = (
        "Usa percent-encoding (RFC 3986) o IDN/punycode para hosts. "
        "Las URLs con caracteres no-ASCII pueden romper en clientes antiguos."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/url-structure",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # Pre-filtramos con un regex que captura percent-encoded non-ASCII
        # (`%80..%FF`) â€” barato en DuckDB. El test definitivo de bytes >= 0x80
        # se hace en Python encoding a UTF-8.
        rows = con.execute("SELECT url_id, url FROM urls").fetchall()
        for url_id, url in rows:
            try:
                encoded = url.encode("utf-8")
            except UnicodeEncodeError:
                continue
            has_raw_non_ascii = any(b >= 0x80 for b in encoded)
            has_pct_non_ascii = False
            # detectar `%XX` con XX >= 80
            i = 0
            while i < len(url) - 2:
                if url[i] == "%":
                    hex_part = url[i + 1 : i + 3]
                    if len(hex_part) == 2 and all(
                        c in "0123456789abcdefABCDEF" for c in hex_part
                    ):
                        if int(hex_part, 16) >= 0x80:
                            has_pct_non_ascii = True
                            break
                i += 1
            if not (has_raw_non_ascii or has_pct_non_ascii):
                continue
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={"url": url},
                message=f"URL con caracteres no-ASCII: {url}",
            )
