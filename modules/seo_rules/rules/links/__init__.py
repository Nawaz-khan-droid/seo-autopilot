"""Links / Internal Linking rules."""

from modules.seo_rules.rules.links import (  # noqa: F401
    internal_nofollow_inlinks_only,
    internal_nofollow_outlinks,
    link_empty_href,
    link_malformed_href,
    link_non_http_protocol,
    link_to_local_path,
    link_whitespace_in_href,
    mixed_follow_nofollow_inlinks,
    non_indexable_page_inlinks_only,
    outlinks_to_localhost,
    pages_high_crawl_depth,
    pages_high_external_outlinks,
    pages_high_internal_outlinks,
    pages_without_internal_outlinks,
)
