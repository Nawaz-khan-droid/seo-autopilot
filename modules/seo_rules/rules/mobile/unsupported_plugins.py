"""Unsupported plugins (Flash, Silverlight, applet, embed/object).

# TODO(schema): requires extraction of <embed>, <object>, <applet> tags.
Schema does not currently track plugin elements.
"""

from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class UnsupportedPlugins(Rule):
    id = "unsupported_plugins"
    name = "Unsupported Plugins"
    category = "Mobile"
    severity = "warning"
    description = "PÃ¡gina usa plugins no soportados en mÃ³vil (<embed>, <object>, <applet>)."
    fix_guidance = (
        "Sustituye Flash/Silverlight/Java applets por HTML5/CSS/JS. Los mÃ³viles "
        "modernos no ejecutan estos plugins y la pÃ¡gina serÃ¡ no mobile-friendly."
    )
    references = [
        "https://web.dev/articles/responsive-web-design-basics",
    ]
    enabled_by_default = False

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # placeholder query â€” needs <embed>/<object>/<applet> tracking
        return iter([])
