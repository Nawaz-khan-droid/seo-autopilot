from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class BadContentType(Rule):
    id = "bad_content_type"
    name = "Bad Content Type"
    category = "Security"
    severity = "warning"
    description = (
        "El header `Content-Type` no coincide con la extensiÃ³n de la URL "
        "(p.ej. `.html` servido como `text/plain`)."
    )
    fix_guidance = (
        "Configura el servidor para enviar el `Content-Type` correcto segÃºn "
        "la extensiÃ³n: `text/html` para .html, `application/javascript` para .js, "
        "`text/css` para .css, `image/*` para imÃ¡genes, etc."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/Security",
    ]

    # ExtensiÃ³n â†’ prefijo esperado del Content-Type.
    _EXPECTED: dict[str, str] = {
        "html": "text/html",
        "htm":  "text/html",
        "xhtml": "application/xhtml+xml",
        "css":  "text/css",
        "js":   "javascript",   # tanto application/javascript como text/javascript
        "mjs":  "javascript",
        "json": "json",
        "xml":  "xml",
        "pdf":  "application/pdf",
        "png":  "image/png",
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "gif":  "image/gif",
        "webp": "image/webp",
        "avif": "image/avif",
        "svg":  "image/svg",
        "ico":  "image/",
        "woff": "font/woff",
        "woff2": "font/woff2",
        "ttf":  "font",
        "otf":  "font",
        "mp4":  "video/mp4",
        "webm": "video/webm",
        "mp3":  "audio/mpeg",
        "wav":  "audio/wav",
        "txt":  "text/plain",
        "csv":  "text/csv",
    }

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            r"""
            SELECT url_id, url, content_type
            FROM urls
            WHERE content_type IS NOT NULL
              AND regexp_matches(url, '\.[A-Za-z0-9]{2,5}($|\?|#)')
            """
        ).fetchall()
        for url_id, url, content_type in rows:
            # Extraer extensiÃ³n: parte tras el Ãºltimo '.', antes de '?' o '#'.
            path = url.split("#", 1)[0].split("?", 1)[0]
            if "/" in path:
                last_segment = path.rsplit("/", 1)[1]
            else:
                last_segment = path
            if "." not in last_segment:
                continue
            ext = last_segment.rsplit(".", 1)[1].lower()
            expected = self._EXPECTED.get(ext)
            if expected is None:
                continue
            ct_lower = content_type.lower()
            if expected in ct_lower:
                continue
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "extension": ext,
                    "content_type": content_type,
                    "expected_substring": expected,
                },
                message=(
                    f"Content-Type {content_type!r} no coincide con la "
                    f"extensiÃ³n .{ext} en {url}"
                ),
            )
