"""Content rules."""

from modules.seo_rules.rules.content import broken_invalid_html  # noqa: F401
from modules.seo_rules.rules.content import content_exact_duplicates  # noqa: F401
from modules.seo_rules.rules.content import content_near_duplicates  # noqa: F401
from modules.seo_rules.rules.content import content_semantically_similar  # noqa: F401
from modules.seo_rules.rules.content import content_technically_duplicate  # noqa: F401
from modules.seo_rules.rules.content import content_title_meta_dup  # noqa: F401
from modules.seo_rules.rules.content import grammar_errors  # noqa: F401
from modules.seo_rules.rules.content import html_missing_or_empty  # noqa: F401
from modules.seo_rules.rules.content import lorem_ipsum  # noqa: F401
from modules.seo_rules.rules.content import low_content_pages  # noqa: F401
from modules.seo_rules.rules.content import low_relevance_content  # noqa: F401
from modules.seo_rules.rules.content import readability_difficult  # noqa: F401
from modules.seo_rules.rules.content import readability_very_difficult  # noqa: F401
from modules.seo_rules.rules.content import soft_404  # noqa: F401
from modules.seo_rules.rules.content import spelling_errors  # noqa: F401
