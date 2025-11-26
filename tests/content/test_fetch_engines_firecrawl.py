"""Tests for Firecrawl fetch engine."""

import os
from unittest.mock import MagicMock, patch

import pytest

from kurt.content.fetch.engines_firecrawl import _extract_metadata, fetch_with_firecrawl


class TestExtractMetadata:
    """Test metadata extraction helper."""

    def test_extract_metadata_with_title(self):
        """Test extracting metadata with title field."""
        mock_result = MagicMock()
        mock_result.metadata = {"title": "Test Title", "author": "Test Author"}

        metadata = _extract_metadata(mock_result)

        assert metadata["title"] == "Test Title"
        assert metadata["author"] == "Test Author"

    def test_extract_metadata_with_og_title(self):
        """Test extracting title from ogTitle field."""
        mock_result = MagicMock()
        mock_result.metadata = {"ogTitle": "OG Title", "description": "Test"}

        metadata = _extract_metadata(mock_result)

        assert metadata["title"] == "OG Title"
        assert metadata["description"] == "Test"

    def test_extract_metadata_with_twitter_title(self):
        """Test extracting title from twitter:title field."""
        mock_result = MagicMock()
        mock_result.metadata = {"twitter:title": "Twitter Title"}

        metadata = _extract_metadata(mock_result)

        assert metadata["title"] == "Twitter Title"

    def test_extract_metadata_priority_order(self):
        """Test that direct title takes precedence over alternate keys."""
        mock_result = MagicMock()
        mock_result.metadata = {
            "title": "Direct Title",
            "ogTitle": "OG Title",
            "twitter:title": "Twitter Title",
        }

        metadata = _extract_metadata(mock_result)

        assert metadata["title"] == "Direct Title"

    def test_extract_metadata_empty(self):
        """Test extracting metadata when none present."""
        mock_result = MagicMock()
        mock_result.metadata = {}

        metadata = _extract_metadata(mock_result)

        assert metadata == {}

    def test_extract_metadata_no_metadata_attr(self):
        """Test extracting when no metadata attribute."""
        mock_result = MagicMock()
        del mock_result.metadata

        metadata = _extract_metadata(mock_result)

        assert metadata == {}


class TestFetchWithFirecrawlSingle:
    """Test single URL fetching."""

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_single_url_success(self, mock_firecrawl_app):
        """Test successful single URL fetch."""
        # Setup mock
        mock_app = MagicMock()
        mock_result = MagicMock()
        mock_result.markdown = "# Test Content\n\nTest body"
        mock_result.metadata = {"title": "Test Title"}
        mock_app.scrape.return_value = mock_result
        mock_firecrawl_app.return_value = mock_app

        # Call function
        content, metadata = fetch_with_firecrawl("https://example.com")

        # Verify
        assert content == "# Test Content\n\nTest body"
        assert metadata["title"] == "Test Title"
        mock_app.scrape.assert_called_once_with("https://example.com", formats=["markdown", "html"])

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_single_url_no_content(self, mock_firecrawl_app):
        """Test single URL fetch with no content."""
        # Setup mock
        mock_app = MagicMock()
        mock_result = MagicMock()
        del mock_result.markdown
        mock_app.scrape.return_value = mock_result
        mock_firecrawl_app.return_value = mock_app

        # Call function and expect error
        with pytest.raises(ValueError, match="No content extracted"):
            fetch_with_firecrawl("https://example.com")

    @patch.dict(os.environ, {}, clear=True)
    def test_fetch_single_url_no_api_key(self):
        """Test single URL fetch without API key."""
        with pytest.raises(ValueError, match="FIRECRAWL_API_KEY not set"):
            fetch_with_firecrawl("https://example.com")

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_single_url_api_error(self, mock_firecrawl_app):
        """Test single URL fetch with API error."""
        # Setup mock
        mock_app = MagicMock()
        mock_app.scrape.side_effect = Exception("API Error")
        mock_firecrawl_app.return_value = mock_app

        # Call function and expect error
        with pytest.raises(ValueError, match="API error"):
            fetch_with_firecrawl("https://example.com")


class TestFetchWithFirecrawlBatch:
    """Test batch URL fetching."""

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_batch_urls_success(self, mock_firecrawl_app):
        """Test successful batch URL fetch."""
        # Setup mock
        mock_app = MagicMock()
        mock_item1 = MagicMock()
        mock_item1.url = "https://example.com/page1"
        mock_item1.markdown = "# Page 1"
        mock_item1.metadata = {"title": "Page 1"}
        mock_item2 = MagicMock()
        mock_item2.url = "https://example.com/page2"
        mock_item2.markdown = "# Page 2"
        mock_item2.metadata = {"title": "Page 2"}

        mock_response = MagicMock()
        mock_response.data = [mock_item1, mock_item2]
        mock_response.invalid_urls = []
        mock_app.batch_scrape.return_value = mock_response
        mock_firecrawl_app.return_value = mock_app

        # Call function
        urls = ["https://example.com/page1", "https://example.com/page2"]
        results = fetch_with_firecrawl(urls)

        # Verify
        assert len(results) == 2
        assert "https://example.com/page1" in results
        assert "https://example.com/page2" in results

        content1, metadata1 = results["https://example.com/page1"]
        assert content1 == "# Page 1"
        assert metadata1["title"] == "Page 1"

        content2, metadata2 = results["https://example.com/page2"]
        assert content2 == "# Page 2"
        assert metadata2["title"] == "Page 2"

        mock_app.batch_scrape.assert_called_once()

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_batch_with_invalid_urls(self, mock_firecrawl_app):
        """Test batch fetch with some invalid URLs."""
        # Setup mock
        mock_app = MagicMock()
        mock_item = MagicMock()
        mock_item.url = "https://example.com/page1"
        mock_item.markdown = "# Page 1"
        mock_item.metadata = {"title": "Page 1"}

        mock_response = MagicMock()
        mock_response.data = [mock_item]
        mock_response.invalid_urls = ["https://invalid.com"]
        mock_app.batch_scrape.return_value = mock_response
        mock_firecrawl_app.return_value = mock_app

        # Call function
        urls = ["https://example.com/page1", "https://invalid.com"]
        results = fetch_with_firecrawl(urls)

        # Verify
        assert len(results) == 2
        assert "https://example.com/page1" in results
        assert "https://invalid.com" in results

        # Valid URL should have content
        content, metadata = results["https://example.com/page1"]
        assert content == "# Page 1"

        # Invalid URL should have exception
        assert isinstance(results["https://invalid.com"], ValueError)

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_batch_with_no_content_items(self, mock_firecrawl_app):
        """Test batch fetch where some items have no content."""
        # Setup mock
        mock_app = MagicMock()
        mock_item1 = MagicMock()
        mock_item1.url = "https://example.com/page1"
        mock_item1.markdown = "# Page 1"
        mock_item1.metadata = {"title": "Page 1"}

        mock_item2 = MagicMock()
        mock_item2.url = "https://example.com/page2"
        del mock_item2.markdown  # No content

        mock_response = MagicMock()
        mock_response.data = [mock_item1, mock_item2]
        mock_response.invalid_urls = []
        mock_app.batch_scrape.return_value = mock_response
        mock_firecrawl_app.return_value = mock_app

        # Call function
        urls = ["https://example.com/page1", "https://example.com/page2"]
        results = fetch_with_firecrawl(urls)

        # Verify
        assert len(results) == 2

        # First URL should succeed
        content1, metadata1 = results["https://example.com/page1"]
        assert content1 == "# Page 1"

        # Second URL should have exception
        assert isinstance(results["https://example.com/page2"], ValueError)

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_batch_api_error(self, mock_firecrawl_app):
        """Test batch fetch with API error."""
        # Setup mock
        mock_app = MagicMock()
        mock_app.batch_scrape.side_effect = Exception("API Error")
        mock_firecrawl_app.return_value = mock_app

        # Call function
        urls = ["https://example.com/page1", "https://example.com/page2"]
        results = fetch_with_firecrawl(urls)

        # Verify all URLs have exceptions
        assert len(results) == 2
        assert all(isinstance(v, ValueError) for v in results.values())

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    def test_fetch_empty_batch(self):
        """Test batch fetch with empty list."""
        results = fetch_with_firecrawl([])
        assert results == {}

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_batch_with_custom_params(self, mock_firecrawl_app):
        """Test batch fetch with custom max_concurrency and batch_size."""
        # Setup mock
        mock_app = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.invalid_urls = []
        mock_app.batch_scrape.return_value = mock_response
        mock_firecrawl_app.return_value = mock_app

        # Call function with custom params
        urls = ["https://example.com/page1"]
        fetch_with_firecrawl(urls, max_concurrency=5, batch_size=50)

        # Verify custom params were passed
        call_args = mock_app.batch_scrape.call_args
        assert call_args.kwargs["max_concurrency"] == 5
