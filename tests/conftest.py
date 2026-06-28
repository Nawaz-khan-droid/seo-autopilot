from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_serp_client():
    with patch("modules.serp_client.SerpClient", autospec=True) as mock:
        client = mock.return_value
        client.search.return_value = SAMPLE_SERP_RESPONSE
        yield client


@pytest.fixture
def mock_groq_client():
    with patch("modules.groq_client.GroqClient", autospec=True) as mock:
        client = mock.return_value
        client.chat.return_value = SAMPLE_GROQ_RESPONSE
        yield client


@pytest.fixture
def mock_pagespeed_client():
    with patch("modules.pagespeed.PageSpeedClient", autospec=True) as mock:
        client = mock.return_value
        client.analyze_both.return_value = {
            "mobile": 65.4,
            "desktop": 82.1,
        }
        yield client


@pytest.fixture
def mock_gsc_client():
    with patch(
        "modules.search_console.SearchConsoleClient", autospec=True
    ) as mock:
        client = mock.return_value
        client.query.return_value = {
            "status": "ok",
            "total_clicks": 142,
            "total_impressions": 8430,
            "rows": [],
        }
        yield client


@pytest.fixture
def mock_analytics_client():
    with patch("modules.ga4_client.AnalyticsClient", autospec=True) as mock:
        client = mock.return_value
        client.get_metrics.return_value = {
            "organic_users": 1200,
            "sessions": 1800,
            "engaged_sessions": 950,
        }
        yield client


@pytest.fixture
def mock_sheet_client():
    sheet = MagicMock()

    def make_ws(records):
        ws = MagicMock()
        ws.get_all_records.return_value = records
        ws.row_values.return_value = []
        return ws

    sheet.get_tab.side_effect = lambda name: make_ws([])
    return sheet


SAMPLE_SERP_RESPONSE = {
    "organic_results": [
        {
            "position": 1,
            "link": "https://www.example.com/page1",
            "title": "Example Page 1",
        },
        {
            "position": 2,
            "link": "https://www.competitor.com/page",
            "title": "Competitor Page",
        },
        {
            "position": 3,
            "link": "https://www.target-site.com/products",
            "title": "Target Product",
        },
        {
            "position": 4,
            "link": "https://www.other-site.com/page",
            "title": "Other Result",
        },
    ]
}

SAMPLE_GROQ_RESPONSE = (
    "Change: Dropped 2 positions from rank 1 to rank 3\n"
    "Cause: Competitor published updated content with better internal linking\n"
    "Recommendation: Refresh the page content and add 3 internal links from high-authority pages\n"
    "Priority: High"
)

SAMPLE_SEARCHAPI_RESPONSE = {
    "organic_results": [
        {
            "position": 7,
            "link": "https://www.target-site.com/services",
            "title": "Target Product",
        },
        {
            "position": 8,
            "link": "https://www.other-site.com/page",
            "title": "Other Result",
        },
    ]
}

SAMPLE_KEYWORDS_RECORDS = [
    {
        "Keyword": "seo services mumbai",
        "Target URL": "https://www.target-site.com/services",
        "Location": "Mumbai",
        "Device": "Desktop",
        "Search Intent": "Local Commercial",
        "Active": "TRUE",
    },
    {
        "Keyword": "digital marketing agency",
        "Target URL": "https://www.target-site.com/about",
        "Location": "Pune",
        "Device": "Mobile",
        "Search Intent": "Commercial",
        "Active": "TRUE",
    },
    {
        "Keyword": "content writing tips",
        "Target URL": "",
        "Location": "Mumbai",
        "Device": "Desktop",
        "Search Intent": "",
        "Active": "TRUE",
    },
]

# Apify batch response — keyword -> parsed item dict shape used by
# the workflow. `organic_results` reused for rank; `ai_overview` and
# `people_also_ask` for feature block harvesting.
SAMPLE_APIFY_BATCH = {
    "seo services mumbai": {
        "organic_results": [
            {"position": 1, "link": "https://www.target-site.com/services", "title": "Target"},
            {"position": 2, "link": "https://www.competitor.com/page", "title": "Competitor"},
        ],
        "ai_overview": {
            "content": "Some AI overview text",
            "sources": [
                {"url": "https://www.target-site.com/services", "title": "Target", "description": ""}
            ],
        },
        "people_also_ask": [
            {"question": "How much does SEO cost?", "answer": None, "url": None, "title": None}
        ],
    },
    "digital marketing agency": {
        "organic_results": [
            {"position": 5, "link": "https://www.other-site.com/page", "title": "Other"},
        ],
        "ai_overview": None,
        "people_also_ask": [],
    },
}

# Apify batch response with no AI Overview returned (key absent).
SAMPLE_APIFY_BATCH_NO_AI = {
    "seo services mumbai": {
        "organic_results": [],
        "ai_overview": None,
        "people_also_ask": [],
    },
}
