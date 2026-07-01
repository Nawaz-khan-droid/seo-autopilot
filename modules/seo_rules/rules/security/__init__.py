"""Security rules."""

from modules.seo_rules.rules.security import bad_content_type  # noqa: F401
from modules.seo_rules.rules.security import form_on_http_url  # noqa: F401
from modules.seo_rules.rules.security import form_url_insecure  # noqa: F401
from modules.seo_rules.rules.security import http_password_field  # noqa: F401
from modules.seo_rules.rules.security import http_url  # noqa: F401
from modules.seo_rules.rules.security import https_links_to_http  # noqa: F401
from modules.seo_rules.rules.security import missing_csp_header  # noqa: F401
from modules.seo_rules.rules.security import missing_hsts_header  # noqa: F401
from modules.seo_rules.rules.security import missing_referrer_policy  # noqa: F401
from modules.seo_rules.rules.security import missing_x_content_type_options  # noqa: F401
from modules.seo_rules.rules.security import missing_x_frame_options  # noqa: F401
from modules.seo_rules.rules.security import mixed_content  # noqa: F401
from modules.seo_rules.rules.security import protocol_relative_resource  # noqa: F401
from modules.seo_rules.rules.security import unsafe_cross_origin_links  # noqa: F401
