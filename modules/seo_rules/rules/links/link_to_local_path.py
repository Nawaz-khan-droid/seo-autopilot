from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class LinkToLocalPath(Rule):
    id = "link_to_local_path"
    name = "Link To Local Path"
    category = "Links"
    severity = "critical"
    description = "Link apunta a un path local del sistema (file://, UNC \\\\server\\share)."
    fix_guidance = (
        "Reemplaza file:// y rutas UNC por URLs HTTP(S) accesibles. "
        "Estos enlaces sÃ³lo funcionan en el equipo del autor."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            r"""
            SELECT source_url_id, target_url, anchor
            FROM links
            WHERE target_url LIKE 'file://%'
               OR target_url LIKE '\\%' ESCAPE '\'
               OR target_url LIKE '%\\\\%'
            """
        ).fetchall()
        for source_url_id, target_url, anchor in rows:
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={"target_url": target_url, "anchor": anchor},
                message=f"Link a path local detectado: {target_url}",
            )
