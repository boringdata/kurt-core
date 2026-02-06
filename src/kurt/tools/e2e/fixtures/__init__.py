"""Test fixtures for e2e tests.

Contains real API response structures for testing when APIs are unavailable,
and golden test data for validation.
"""

from kurt.tools.e2e.fixtures.apify_responses import (
    WEBSITE_CRAWLER_RESPONSE,
    WEBSITE_CRAWLER_MULTI_PAGE,
    TWITTER_SEARCH_RESPONSE,
    TWITTER_PROFILE_RESPONSE,
    LINKEDIN_POST_RESPONSE,
    SUBSTACK_NEWSLETTER_RESPONSE,
    QUOTA_EXCEEDED_ERROR,
    AUTH_ERROR,
    ACTOR_NOT_FOUND_ERROR,
)

from kurt.tools.e2e.fixtures.golden_data import (
    # Map engine golden data
    GOLDEN_SITEMAP_RESULT,
    GOLDEN_RSS_RESULT,
    GOLDEN_CRAWL_RESULT,
    # Fetch engine golden data
    GOLDEN_TRAFILATURA_RESULT,
    GOLDEN_HTTPX_RESULT,
    GOLDEN_TAVILY_RESULT,
    # Pipeline golden data
    GOLDEN_SITEMAP_FETCH_PIPELINE,
    GOLDEN_RSS_FETCH_PIPELINE,
    GOLDEN_CRAWL_FETCH_PIPELINE,
    # Content snapshots
    GOLDEN_EXAMPLE_COM_CONTENT,
    GOLDEN_PYTHON_DOCS_JSON,
    GOLDEN_PYTHON_ORG_ABOUT,
    # Error cases
    GOLDEN_404_RESPONSE,
    GOLDEN_INVALID_URL,
    GOLDEN_NO_SITEMAP,
    # Validation helpers
    validate_map_result,
    validate_fetch_result,
    validate_content_snapshot,
)

__all__ = [
    # Apify fixtures
    "WEBSITE_CRAWLER_RESPONSE",
    "WEBSITE_CRAWLER_MULTI_PAGE",
    "TWITTER_SEARCH_RESPONSE",
    "TWITTER_PROFILE_RESPONSE",
    "LINKEDIN_POST_RESPONSE",
    "SUBSTACK_NEWSLETTER_RESPONSE",
    "QUOTA_EXCEEDED_ERROR",
    "AUTH_ERROR",
    "ACTOR_NOT_FOUND_ERROR",
    # Map engine golden data
    "GOLDEN_SITEMAP_RESULT",
    "GOLDEN_RSS_RESULT",
    "GOLDEN_CRAWL_RESULT",
    # Fetch engine golden data
    "GOLDEN_TRAFILATURA_RESULT",
    "GOLDEN_HTTPX_RESULT",
    "GOLDEN_TAVILY_RESULT",
    # Pipeline golden data
    "GOLDEN_SITEMAP_FETCH_PIPELINE",
    "GOLDEN_RSS_FETCH_PIPELINE",
    "GOLDEN_CRAWL_FETCH_PIPELINE",
    # Content snapshots
    "GOLDEN_EXAMPLE_COM_CONTENT",
    "GOLDEN_PYTHON_DOCS_JSON",
    "GOLDEN_PYTHON_ORG_ABOUT",
    # Error cases
    "GOLDEN_404_RESPONSE",
    "GOLDEN_INVALID_URL",
    "GOLDEN_NO_SITEMAP",
    # Validation helpers
    "validate_map_result",
    "validate_fetch_result",
    "validate_content_snapshot",
]
