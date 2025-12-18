"""
Unit tests for web fetch utility.

Tests fetch_from_web function with mocked engines.
"""

from unittest.mock import patch

import pytest

from kurt.content.ingestion.utils.web import fetch_from_web


class TestFetchFromWeb:
    """Tests for fetch_from_web function."""

    @patch("kurt.content.ingestion.utils.web.fetch_with_trafilatura")
    def test_fetch_with_trafilatura_engine(self, mock_fetch):
        """Test fetching with trafilatura engine."""
        mock_fetch.return_value = ("# Content", {"title": "Test"})

        content, metadata = fetch_from_web(
            "https://example.com/page",
            fetch_engine="trafilatura",
        )

        assert content == "# Content"
        assert metadata["title"] == "Test"
        mock_fetch.assert_called_once_with("https://example.com/page")

    @patch("kurt.content.ingestion.utils.web.fetch_with_httpx")
    def test_fetch_with_httpx_engine(self, mock_fetch):
        """Test fetching with httpx engine."""
        mock_fetch.return_value = ("# Content", {"title": "Test"})

        content, metadata = fetch_from_web(
            "https://example.com/page",
            fetch_engine="httpx",
        )

        assert content == "# Content"
        mock_fetch.assert_called_once_with("https://example.com/page")

    @patch("kurt.content.ingestion.utils.web.fetch_with_firecrawl")
    def test_fetch_with_firecrawl_engine(self, mock_fetch):
        """Test fetching with firecrawl engine."""
        mock_fetch.return_value = ("# Content", {"title": "Test"})

        content, metadata = fetch_from_web(
            "https://example.com/page",
            fetch_engine="firecrawl",
        )

        assert content == "# Content"
        mock_fetch.assert_called_once_with("https://example.com/page")

    @patch("kurt.content.ingestion.utils.web.fetch_with_trafilatura")
    def test_fetch_default_engine_is_trafilatura(self, mock_fetch):
        """Test that default engine is trafilatura."""
        mock_fetch.return_value = ("# Content", {})

        fetch_from_web("https://example.com/page", fetch_engine="unknown")

        # Unknown engine falls through to trafilatura (else branch)
        mock_fetch.assert_called_once()

    @patch("kurt.content.ingestion.utils.web.parse_source_identifier")
    def test_raises_error_for_cms_url_pattern(self, mock_parse):
        """Test that CMS URL patterns raise error."""
        mock_parse.return_value = ("cms", {"platform": "sanity"})

        with pytest.raises(ValueError, match="CMS URL pattern detected"):
            fetch_from_web("sanity/prod/article/123", fetch_engine="trafilatura")

    @patch("kurt.content.ingestion.utils.web.fetch_with_trafilatura")
    def test_fetch_propagates_engine_errors(self, mock_fetch):
        """Test that engine errors propagate correctly."""
        mock_fetch.side_effect = ValueError("Network timeout")

        with pytest.raises(ValueError, match="Network timeout"):
            fetch_from_web("https://example.com/page", fetch_engine="trafilatura")

    @patch("kurt.content.ingestion.utils.web.fetch_with_trafilatura")
    def test_fetch_returns_empty_metadata(self, mock_fetch):
        """Test fetching when metadata is empty."""
        mock_fetch.return_value = ("# Plain content", {})

        content, metadata = fetch_from_web(
            "https://example.com/page",
            fetch_engine="trafilatura",
        )

        assert content == "# Plain content"
        assert metadata == {}
