from collections.abc import Iterable

from duckdb import DuckDBPyConnection

from modules.seo_rules.rules import Rule, register_rule
from modules.seo_rules.rules._issue import Issue

_SUPPORTED_LANGS = {
    "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az",
    "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo", "br", "bs",
    "ca", "ce", "ch", "co", "cr", "cs", "cu", "cv", "cy",
    "da", "de", "dv", "dz",
    "ee", "el", "en", "eo", "es", "et", "eu",
    "fa", "ff", "fi", "fj", "fo", "fr", "fy",
    "ga", "gd", "gl", "gn", "gu", "gv",
    "ha", "he", "hi", "ho", "hr", "ht", "hu", "hy", "hz",
    "ia", "id", "ie", "ig", "ii", "ik", "io", "is", "it", "iu",
    "ja", "jv",
    "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn", "ko", "kr", "ks", "ku", "kv", "kw", "ky",
    "la", "lb", "lg", "li", "ln", "lo", "lt", "lu", "lv",
    "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my",
    "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv", "ny",
    "oc", "oj", "om", "or", "os",
    "pa", "pi", "pl", "ps", "pt",
    "qu",
    "rm", "rn", "ro", "ru", "rw",
    "sa", "sc", "sd", "se", "sg", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "ss", "st", "su", "sv", "sw",
    "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw", "ty",
    "ug", "uk", "ur", "uz",
    "ve", "vi", "vo",
    "wa", "wo",
    "xh",
    "yi", "yo",
    "za", "zh", "zu",
}


@register_rule
class HreflangUnsupported(Rule):
    id = "hreflang_unsupported"
    name = "Hreflang Unsupported Language Code"
    category = "Hreflang"
    severity = "warning"
    description = (
        "El cÃ³digo de idioma usado en hreflang tiene formato vÃ¡lido pero no "
        "es un cÃ³digo ISO 639-1 reconocido."
    )
    fix_guidance = (
        "Usa el cÃ³digo ISO 639-1 estÃ¡ndar (en, es, fr, de...). Para regiones "
        "especÃ­ficas aÃ±ade el cÃ³digo ISO 3166-1 alpha-2 (en-US, es-MX...)."
    )
    references = [
        "https://developers.google.com/search/docs/specialty/international/localized-versions",
    ]

    def check(self, con: DuckDBPyConnection) -> Iterable[Issue]:
        rows = con.execute(
            """
            SELECT source_url_id, lang, href
            FROM hreflang
            WHERE lang IS NOT NULL
              AND lang <> 'x-default'
              AND lang NOT LIKE '%-%'
              AND length(lang) BETWEEN 2 AND 3
            """
        ).fetchall()
        for source_url_id, lang, href in rows:
            base = lang.lower().split("-", 1)[0]
            if base in _SUPPORTED_LANGS:
                continue
            yield Issue(
                rule_id=self.id,
                url_id=source_url_id,
                severity=self.severity,
                category=self.category,
                evidence={"lang": lang, "href": href},
                message=f"CÃ³digo de idioma no reconocido: {lang!r} (href={href})",
            )
