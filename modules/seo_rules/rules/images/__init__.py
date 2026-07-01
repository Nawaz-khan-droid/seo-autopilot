"""Images rules."""

from modules.seo_rules.rules.images import image_missing_alt_text  # noqa: F401
from modules.seo_rules.rules.images import image_missing_alt_attribute  # noqa: F401
from modules.seo_rules.rules.images import image_background_a11y  # noqa: F401
from modules.seo_rules.rules.images import image_over_100kb  # noqa: F401
from modules.seo_rules.rules.images import image_alt_over_100_chars  # noqa: F401
from modules.seo_rules.rules.images import image_incorrectly_sized  # noqa: F401
from modules.seo_rules.rules.images import image_missing_size_attrs  # noqa: F401
from modules.seo_rules.rules.images import image_anchored_no_alt  # noqa: F401
from modules.seo_rules.rules.images import image_alt_repeats_text  # noqa: F401
