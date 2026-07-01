from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

# Common thin-content threshold used in technical SEO audits.
WORD_COUNT_THRESHOLD = 200


@register_rule
class LowContentPages(Rule):
    id = "low_content_pages"
    name = "Low Content Pages"
    category = "Content"
    severity = "info"
    description = f"URL indexable con menos de {WORD_COUNT_THRESHOLD} palabras."
    fix_guidance = (
        f"AmplÃ­a el contenido a mÃ¡s de {WORD_COUNT_THRESHOLD} palabras o "
        "considera marcar la pÃ¡gina como noindex / consolidar con otra."
    )
    references = [
        "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT url_id, url, word_count
            FROM urls
            WHERE is_indexable = TRUE
              AND word_count IS NOT NULL
              AND word_count < ?
            """,
            [WORD_COUNT_THRESHOLD],
        ).fetchall()
        for url_id, url, wc in rows:
            yield Issue(
                rule_id=self.id,
                url_id=url_id,
                severity=self.severity,
                category=self.category,
                evidence={
                    "url": url,
                    "word_count": wc,
                    "threshold": WORD_COUNT_THRESHOLD,
                },
                message=f"PÃ¡gina con {wc} palabras (<{WORD_COUNT_THRESHOLD}): {url}",
            )
