"""URL rules."""

from modules.seo_rules.rules.url import broken_bookmark  # noqa: F401
from modules.seo_rules.rules.url import query_more_than_three_params  # noqa: F401
from modules.seo_rules.rules.url import query_paginated_params  # noqa: F401
from modules.seo_rules.rules.url import query_search_filter_params  # noqa: F401
from modules.seo_rules.rules.url import query_sort_params  # noqa: F401
from modules.seo_rules.rules.url import url_contains_space  # noqa: F401
from modules.seo_rules.rules.url import url_ga_tracking_params  # noqa: F401
from modules.seo_rules.rules.url import url_has_parameters  # noqa: F401
from modules.seo_rules.rules.url import url_internal_search  # noqa: F401
from modules.seo_rules.rules.url import url_multiple_ga  # noqa: F401
from modules.seo_rules.rules.url import url_multiple_gtm  # noqa: F401
from modules.seo_rules.rules.url import url_multiple_slashes  # noqa: F401
from modules.seo_rules.rules.url import url_no_ga  # noqa: F401
from modules.seo_rules.rules.url import url_no_gtm  # noqa: F401
from modules.seo_rules.rules.url import url_non_ascii  # noqa: F401
from modules.seo_rules.rules.url import url_over_115_chars  # noqa: F401
from modules.seo_rules.rules.url import url_repetitive_path  # noqa: F401
from modules.seo_rules.rules.url import url_repetitive_query_params  # noqa: F401
from modules.seo_rules.rules.url import url_session_id_params  # noqa: F401
from modules.seo_rules.rules.url import url_underscores  # noqa: F401
from modules.seo_rules.rules.url import url_uppercase  # noqa: F401
