"""
Unit tests for fetch engines.

Tests trafilatura and firecrawl engines with mocked HTTP calls.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestFetchWithHttpx:
    """Tests for httpx fetch engine."""

    @patch("httpx.get")
    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    def test_fetch_success(self, mock_extract, mock_metadata, mock_httpx_get):
        """Test successful httpx fetch."""
        from kurt.content.ingestion.engines import fetch_with_httpx

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_httpx_get.return_value = mock_response

        # Mock trafilatura metadata
        mock_metadata_obj = MagicMock()
        mock_metadata_obj.title = "Test Title"
        mock_metadata_obj.author = "Test Author"
        mock_metadata_obj.date = "2024-01-01"
        mock_metadata_obj.description = "Test description"
        mock_metadata_obj.fingerprint = "abc123"
        mock_metadata.return_value = mock_metadata_obj

        # Mock trafilatura extract
        mock_extract.return_value = "# Test Title\n\nTest content"

        # Execute
        content, metadata = fetch_with_httpx("https://example.com/test")

        # Verify
        assert content == "# Test Title\n\nTest content"
        assert metadata["title"] == "Test Title"
        assert metadata["author"] == "Test Author"
        mock_httpx_get.assert_called_once_with(
            "https://example.com/test", follow_redirects=True, timeout=30.0
        )

    @patch("httpx.get")
    def test_fetch_http_error(self, mock_httpx_get):
        """Test httpx fetch with HTTP error."""
        from kurt.content.ingestion.engines import fetch_with_httpx

        mock_httpx_get.side_effect = Exception("Connection timeout")

        with pytest.raises(ValueError, match=r"\[httpx\] Download error"):
            fetch_with_httpx("https://example.com/test")

    @patch("httpx.get")
    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    def test_fetch_no_content_extracted(self, mock_extract, mock_metadata, mock_httpx_get):
        """Test httpx fetch when trafilatura extracts no content."""
        from kurt.content.ingestion.engines import fetch_with_httpx

        mock_response = MagicMock()
        mock_response.text = "<html><body>Paywall</body></html>"
        mock_httpx_get.return_value = mock_response

        mock_metadata.return_value = None
        mock_extract.return_value = None

        with pytest.raises(ValueError, match=r"\[httpx\] No content extracted"):
            fetch_with_httpx("https://example.com/paywall")


class TestFetchWithTrafilatura:
    """Tests for trafilatura fetch engine."""

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    def test_fetch_success(self, mock_extract, mock_metadata, mock_fetch_url):
        """Test successful trafilatura fetch."""
        from kurt.content.ingestion.engines import fetch_with_trafilatura

        mock_fetch_url.return_value = "<html><body>Test content</body></html>"

        mock_metadata_obj = MagicMock()
        mock_metadata_obj.title = "Test Title"
        mock_metadata_obj.author = "Test Author"
        mock_metadata_obj.date = "2024-01-01"
        mock_metadata_obj.description = "Test description"
        mock_metadata_obj.fingerprint = "abc123"
        mock_metadata.return_value = mock_metadata_obj

        mock_extract.return_value = "# Test Title\n\nTest content"

        content, metadata = fetch_with_trafilatura("https://example.com/test")

        assert content == "# Test Title\n\nTest content"
        assert metadata["title"] == "Test Title"
        mock_fetch_url.assert_called_once_with("https://example.com/test")

    @patch("trafilatura.fetch_url")
    def test_fetch_download_error(self, mock_fetch_url):
        """Test trafilatura fetch with download error."""
        from kurt.content.ingestion.engines import fetch_with_trafilatura

        mock_fetch_url.side_effect = Exception("Connection timeout")

        with pytest.raises(ValueError, match=r"\[Trafilatura\] Download error"):
            fetch_with_trafilatura("https://example.com/test")

    @patch("trafilatura.fetch_url")
    def test_fetch_no_content_returned(self, mock_fetch_url):
        """Test trafilatura fetch when download returns nothing."""
        from kurt.content.ingestion.engines import fetch_with_trafilatura

        mock_fetch_url.return_value = None

        with pytest.raises(ValueError, match=r"\[Trafilatura\] Failed to download"):
            fetch_with_trafilatura("https://example.com/test")

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    def test_fetch_no_content_extracted(self, mock_extract, mock_metadata, mock_fetch_url):
        """Test trafilatura fetch when extraction returns nothing."""
        from kurt.content.ingestion.engines import fetch_with_trafilatura

        mock_fetch_url.return_value = "<html><body>Paywall</body></html>"
        mock_metadata.return_value = None
        mock_extract.return_value = None

        with pytest.raises(ValueError, match=r"\[Trafilatura\] No content extracted"):
            fetch_with_trafilatura("https://example.com/paywall")

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    def test_fetch_empty_metadata(self, mock_extract, mock_metadata, mock_fetch_url):
        """Test trafilatura fetch with no metadata."""
        from kurt.content.ingestion.engines import fetch_with_trafilatura

        mock_fetch_url.return_value = "<html><body>Content</body></html>"
        mock_metadata.return_value = None  # No metadata
        mock_extract.return_value = "Plain content"

        content, metadata = fetch_with_trafilatura("https://example.com/test")

        assert content == "Plain content"
        assert metadata == {}


class TestFetchWithFirecrawl:
    """Tests for firecrawl fetch engine."""

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_success(self, mock_firecrawl_class):
        """Test successful firecrawl fetch."""
        from kurt.content.ingestion.engines import fetch_with_firecrawl

        # Mock FirecrawlApp instance
        mock_app = MagicMock()
        mock_firecrawl_class.return_value = mock_app

        # Mock scrape response (firecrawl returns object with attributes)
        mock_result = MagicMock()
        mock_result.markdown = "# Test Title\n\nTest content"
        mock_result.metadata = {
            "title": "Test Title",
            "author": "Test Author",
        }
        mock_app.scrape.return_value = mock_result

        content, metadata = fetch_with_firecrawl("https://example.com/test")

        assert content == "# Test Title\n\nTest content"
        assert metadata["title"] == "Test Title"
        mock_app.scrape.assert_called_once()

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_no_markdown(self, mock_firecrawl_class):
        """Test firecrawl fetch when no markdown returned."""
        from kurt.content.ingestion.engines import fetch_with_firecrawl

        mock_app = MagicMock()
        mock_firecrawl_class.return_value = mock_app

        # Result without markdown attribute
        mock_result = MagicMock(spec=[])  # No attributes
        mock_app.scrape.return_value = mock_result

        with pytest.raises(ValueError, match="No content extracted"):
            fetch_with_firecrawl("https://example.com/test")

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_api_error(self, mock_firecrawl_class):
        """Test firecrawl fetch with API error."""
        from kurt.content.ingestion.engines import fetch_with_firecrawl

        mock_app = MagicMock()
        mock_firecrawl_class.return_value = mock_app
        mock_app.scrape.side_effect = Exception("API rate limit")

        with pytest.raises(ValueError, match="API error"):
            fetch_with_firecrawl("https://example.com/test")

    @patch.dict(os.environ, {}, clear=True)
    def test_fetch_no_api_key(self):
        """Test firecrawl fetch without API key."""
        from kurt.content.ingestion.engines import fetch_with_firecrawl

        with pytest.raises(ValueError, match="FIRECRAWL_API_KEY not set"):
            fetch_with_firecrawl("https://example.com/test")

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("firecrawl.FirecrawlApp")
    def test_batch_fetch_success(self, mock_firecrawl_class):
        """Test successful batch firecrawl fetch."""
        from kurt.content.ingestion.engines import fetch_with_firecrawl

        mock_app = MagicMock()
        mock_firecrawl_class.return_value = mock_app

        # Mock batch response
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

        results = fetch_with_firecrawl(["https://example.com/page1", "https://example.com/page2"])

        assert len(results) == 2
        assert results["https://example.com/page1"][0] == "# Page 1"
        assert results["https://example.com/page2"][0] == "# Page 2"
