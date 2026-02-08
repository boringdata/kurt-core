"""
Kurt testing utilities for E2E tests.

This package provides mock factories and assertion helpers for testing
CLI commands and workflows without making real external API calls.

Usage:
    from kurt.testing import (
        # Mock factories
        mock_httpx_response,
        mock_sitemap_response,
        mock_perplexity_response,
        mock_reddit_posts,
        mock_hackernews_story,
        mock_apify_actor_run,
        mock_posthog_events,
        mock_feedparser_parse,
        mock_trafilatura_extract,
        # Database assertions
        assert_map_document_exists,
        assert_fetch_document_exists,
        assert_workflow_status,
        assert_row_count,
        # Filesystem assertions
        assert_file_exists,
        assert_directory_exists,
    )

Example E2E test:
    from unittest.mock import patch

    from kurt.testing import (
        mock_sitemap_response,
        assert_map_document_exists,
        assert_map_document_count,
    )

    @patch("httpx.get")
    def test_map_url_creates_documents(mock_get, cli_runner, tmp_project):
        mock_get.return_value = mock_sitemap_response([
            "https://example.com/page1",
            "https://example.com/page2",
        ])

        from kurt.tools.map.cli import map_group
        result = cli_runner.invoke(map_group, ["url", "https://example.com"])
        assert result.exit_code == 0

        from kurt.db import managed_session
        with managed_session() as session:
            assert_map_document_count(session, 2)
            assert_map_document_exists(session, "https://example.com/page1")
"""

from __future__ import annotations

# Re-export all assertion helpers
from kurt.testing.assertions import (
    # Filesystem assertions
    assert_directory_exists,
    # Fetch document assertions
    assert_fetch_document_count,
    assert_fetch_document_exists,
    assert_fetch_document_not_exists,
    assert_fetch_has_content,
    assert_file_contains,
    assert_file_content_matches,
    assert_file_exists,
    assert_file_not_exists,
    # Map document assertions
    assert_map_document_count,
    assert_map_document_exists,
    assert_map_document_not_exists,
    # Generic assertions
    assert_row_count,
    assert_table_empty,
    assert_table_not_empty,
    # Workflow assertions
    assert_workflow_run_count,
    assert_workflow_run_exists,
    assert_workflow_status,
    # Count helpers
    count_documents_by_domain,
    count_documents_by_status,
)

# Re-export all mock factories
from kurt.testing.mocks import (
    # HTTP mocks
    MockHttpxResponse,
    # Apify mocks
    mock_apify_actor_run,
    mock_apify_dataset_items,
    mock_apify_twitter_post,
    mock_apify_twitter_profile,
    # Feedparser mocks
    mock_feedparser_parse,
    # HackerNews mocks
    mock_hackernews_story,
    mock_hackernews_top_stories,
    # HTML mocks
    mock_html_page,
    mock_httpx_error,
    mock_httpx_response,
    # Perplexity mocks
    mock_perplexity_response,
    # PostHog mocks
    mock_posthog_events,
    mock_posthog_insights,
    # Reddit mocks
    mock_reddit_posts,
    # Sitemap/RSS mocks
    mock_rss_response,
    mock_sitemap_index_response,
    mock_sitemap_response,
    # Trafilatura mocks
    mock_trafilatura_extract,
    mock_trafilatura_fetch_url,
)

__all__ = [
    # HTTP mocks
    "MockHttpxResponse",
    "mock_httpx_response",
    "mock_httpx_error",
    # Sitemap/RSS mocks
    "mock_sitemap_response",
    "mock_sitemap_index_response",
    "mock_rss_response",
    # Trafilatura mocks
    "mock_trafilatura_extract",
    "mock_trafilatura_fetch_url",
    # Perplexity mocks
    "mock_perplexity_response",
    # Reddit mocks
    "mock_reddit_posts",
    # HackerNews mocks
    "mock_hackernews_top_stories",
    "mock_hackernews_story",
    # Apify mocks
    "mock_apify_actor_run",
    "mock_apify_dataset_items",
    "mock_apify_twitter_profile",
    "mock_apify_twitter_post",
    # PostHog mocks
    "mock_posthog_events",
    "mock_posthog_insights",
    # Feedparser mocks
    "mock_feedparser_parse",
    # HTML mocks
    "mock_html_page",
    # Map document assertions
    "assert_map_document_exists",
    "assert_map_document_not_exists",
    "assert_map_document_count",
    # Fetch document assertions
    "assert_fetch_document_exists",
    "assert_fetch_document_not_exists",
    "assert_fetch_document_count",
    "assert_fetch_has_content",
    # Workflow assertions
    "assert_workflow_run_exists",
    "assert_workflow_status",
    "assert_workflow_run_count",
    # Generic assertions
    "assert_row_count",
    "assert_table_empty",
    "assert_table_not_empty",
    # Filesystem assertions
    "assert_file_exists",
    "assert_file_not_exists",
    "assert_directory_exists",
    "assert_file_contains",
    "assert_file_content_matches",
    # Count helpers
    "count_documents_by_status",
    "count_documents_by_domain",
]
