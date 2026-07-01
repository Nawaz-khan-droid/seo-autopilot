from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class LinkMalformedHref(Rule):
    id = "link_malformed_href"
    name = "Link Malformed Href"
    category = "Links"
    severity = "warning"
    description = "Atributo href NULL o vacÃ­o en el grafo de links."
    fix_guidance = "Elimina los <a> sin destino o asÃ­gnales un href vÃ¡lido."
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT source_url_id, target_url, anchor
            FROM links
            WHERE target_url IS NULL
               OR target_url = ''
            """
        ).fetchall()
        for source_url_id, target_url, anchor in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={"target_url": target_url, "anchor": anchor},
                message="Link con href vacÃ­o o NULL detectado.",
            )
