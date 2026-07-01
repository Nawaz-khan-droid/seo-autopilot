"""Map our Playwright crawl data into DuckDB rows for rule engine consumption."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from duckdb import DuckDBPyConnection


def url_id(url: str) -> int:
    """Deterministic 64-bit ID from a URL."""
    digest = hashlib.blake2b(url.encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=False)


URL_COLUMNS = [
    "url_id", "url", "final_url", "status_code", "redirect_count",
    "content_type", "content_length", "response_time_ms", "depth",
    "crawled_at", "from_sitemap", "from_robots", "rendered",
    "title", "meta_description", "meta_robots", "canonical", "viewport",
    "charset", "lang", "h1", "h2", "h3", "h4", "h5", "h6",
    "is_indexable", "indexability_reason", "x_robots_tag",
    "word_count", "text_to_html_ratio", "content_hash", "simhash",
    "lcp_ms", "cls", "inp_ms",
    "header_csp", "header_hsts", "header_x_frame_options", "header_referrer_policy",
    "raw_html", "rendered_html",
]


def populate_from_crawl(
    con: DuckDBPyConnection,
    target_url: str,
    crawl_data: dict[str, Any],
) -> None:
    """Insert a URL row + links + images into DuckDB from our Playwright crawl output.

    `crawl_data` is the raw dict from ``_run_playwright_headless``,
    ``_extract_seo_via_urllib``, or similar.
    """
    uid = url_id(target_url)
    now = datetime.now(timezone.utc)

    h1 = crawl_data.get("h1_texts", [])
    h2 = crawl_data.get("h2_texts", [])
    h3 = crawl_data.get("h3_texts", [])
    h4 = crawl_data.get("h4_texts", [])
    h5 = crawl_data.get("h5_texts", [])
    h6 = crawl_data.get("h6_texts", [])

    row = {
        "url_id": uid,
        "url": target_url,
        "final_url": crawl_data.get("final_url", target_url),
        "status_code": crawl_data.get("status_code", 200),
        "redirect_count": crawl_data.get("redirect_count", 0),
        "content_type": crawl_data.get("content_type", "text/html"),
        "content_length": crawl_data.get("content_length") or crawl_data.get("_raw_html_len"),
        "response_time_ms": crawl_data.get("response_time_ms"),
        "depth": 0,
        "crawled_at": now,
        "from_sitemap": False,
        "from_robots": False,
        "rendered": crawl_data.get("rendered", True),
        "title": crawl_data.get("title"),
        "meta_description": crawl_data.get("meta_description"),
        "meta_robots": crawl_data.get("meta_robots"),
        "canonical": crawl_data.get("canonical"),
        "viewport": crawl_data.get("viewport"),
        "charset": crawl_data.get("charset", "utf-8"),
        "lang": crawl_data.get("lang"),
        "h1": h1 or None,
        "h2": h2 or None,
        "h3": h3 or None,
        "h4": h4 or None,
        "h5": h5 or None,
        "h6": h6 or None,
        "is_indexable": crawl_data.get("is_indexable", True),
        "indexability_reason": crawl_data.get("indexability_reason"),
        "x_robots_tag": crawl_data.get("x_robots_tag"),
        "word_count": crawl_data.get("word_count", 0),
        "text_to_html_ratio": crawl_data.get("text_to_html_ratio"),
        "content_hash": crawl_data.get("content_hash"),
        "simhash": None,
        "lcp_ms": None,
        "cls": None,
        "inp_ms": None,
        "header_csp": crawl_data.get("header_csp"),
        "header_hsts": crawl_data.get("header_hsts"),
        "header_x_frame_options": crawl_data.get("header_x_frame_options"),
        "header_referrer_policy": crawl_data.get("header_referrer_policy"),
        "raw_html": None,
        "rendered_html": None,
    }

    values = [row.get(col) for col in URL_COLUMNS]
    placeholders = ",".join(["?"] * len(URL_COLUMNS))
    con.execute(
        f"INSERT OR REPLACE INTO urls ({','.join(URL_COLUMNS)}) VALUES ({placeholders})",
        values,
    )

    # Links
    link_details = crawl_data.get("link_details", [])
    if link_details:
        for i, ld in enumerate(link_details):
            href = ld.get("href", "")
            if not href:
                continue
            con.execute(
                """
                INSERT INTO links (
                    source_url_id, target_url, target_url_id, anchor, rel,
                    link_type, in_navigation, in_footer, position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    uid,
                    href,
                    url_id(href),
                    ld.get("anchor"),
                    ld.get("rel"),
                    ld.get("link_type", "internal" if _is_same_domain(href, target_url) else "external"),
                    ld.get("in_navigation", False),
                    ld.get("in_footer", False),
                    i,
                ],
            )

    # Images as resources
    image_details = crawl_data.get("image_details", [])
    if image_details:
        for img in image_details:
            src = img.get("src", "")
            if not src:
                continue
            try:
                w = int(img.get("width")) if img.get("width") is not None else None
            except (ValueError, TypeError):
                w = None
            try:
                h = int(img.get("height")) if img.get("height") is not None else None
            except (ValueError, TypeError):
                h = None
            con.execute(
                """
                INSERT INTO resources (
                    source_url_id, resource_url, resource_type, status,
                    size_bytes, alt, width, height, loading_attr, format
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    uid,
                    src,
                    "image",
                    img.get("status"),
                    img.get("size_bytes"),
                    img.get("alt"),
                    w,
                    h,
                    img.get("loading"),
                    img.get("format"),
                ],
            )

    # Hreflang
    hreflang_tags = crawl_data.get("hreflang_tags", [])
    if hreflang_tags:
        for ht in hreflang_tags:
            con.execute(
                """
                INSERT INTO hreflang (
                    source_url_id, lang, href, href_url_id,
                    from_html, from_header, from_sitemap
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    uid,
                    ht.get("lang", ""),
                    ht.get("href", ""),
                    url_id(ht.get("href", "")),
                    ht.get("from_html", True),
                    False,
                    False,
                ],
            )

    # Structured data
    schema_blocks = crawl_data.get("schema_blocks", [])
    if schema_blocks:
        for sb in schema_blocks:
            con.execute(
                """
                INSERT INTO structured_data (
                    url_id, syntax, schema_type, data, valid, validation_errors
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    uid,
                    sb.get("syntax", "json-ld"),
                    sb.get("schema_type"),
                    json.dumps(sb.get("data", {})),
                    sb.get("valid", True),
                    sb.get("validation_errors"),
                ],
            )

    # Redirects from link health check or Playwright response handler
    redirects = crawl_data.get("_redirects", [])
    if not redirects:
        lh = crawl_data.get("link_health", {})
        pw_redirects = lh.get("redirects_in_page_load", [])
        if pw_redirects:
            redirects = [
                {"from": rd.get("url", ""), "to": rd.get("location", ""), "status": rd.get("status", 301)}
                for rd in pw_redirects
            ]
    if redirects:
        for i, rd in enumerate(redirects):
            con.execute(
                """
                INSERT INTO redirects (
                    chain_id, from_url, to_url, status_code, hop, is_loop
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [uid, rd.get("from", ""), rd.get("to", ""), rd.get("status", 301), i, False],
            )


def _is_same_domain(url_a: str, url_b: str) -> bool:
    from urllib.parse import urlparse
    try:
        return urlparse(url_a).netloc.lower() == urlparse(url_b).netloc.lower()
    except Exception:
        return False
