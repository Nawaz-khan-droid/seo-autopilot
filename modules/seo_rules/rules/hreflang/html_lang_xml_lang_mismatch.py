from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue


@register_rule
class HtmlLangXmlLangMismatch(Rule):
    id = "html_lang_xml_lang_mismatch"
    name = "HTML lang and xml:lang mismatch"
    category = "Hreflang"
    severity = "info"
    enabled_by_default = False  # TODO(schema): xml:lang not extracted yet
    description = (
        "El atributo lang del HTML y el atributo xml:lang declaran valores "
        "distintos."
    )
    fix_guidance = (
        "Si declaras ambos lang y xml:lang, deben coincidir. Lo mÃ¡s comÃºn es "
        "dejar solo lang."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        # TODO(schema): requires xml:lang column extraction
        return iter([])
