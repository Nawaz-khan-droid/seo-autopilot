"""Orphan / Isolated Pages rules."""

from modules.seo_rules.rules.orphans import (  # noqa: F401
    isolated_chain,
    isolated_via_canonical,
    isolated_via_noindex_follow,
    isolated_via_redirect,
    orphan_url,
)
