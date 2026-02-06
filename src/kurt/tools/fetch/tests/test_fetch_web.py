"""Tests for fetch engines."""

from unittest.mock import MagicMock, patch

import pytest


class TestFetchEngines:
    """Test suite for fetch engine classes."""

    def test_trafilatura_fetcher_import(self):
        """Test that TrafilaturaFetcher can be imported."""
        from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher

        assert TrafilaturaFetcher is not None

    def test_httpx_fetcher_import(self):
        """Test that HttpxFetcher can be imported."""
        from kurt.tools.fetch.engines.httpx import HttpxFetcher

        assert HttpxFetcher is not None

    def test_tavily_fetcher_import(self):
        """Test that TavilyFetcher can be imported."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        assert TavilyFetcher is not None

    def test_firecrawl_fetcher_import(self):
        """Test that FirecrawlFetcher can be imported."""
        from kurt.tools.fetch.engines.firecrawl import FirecrawlFetcher

        assert FirecrawlFetcher is not None

    @patch("kurt.tools.fetch.utils.trafilatura")
    @patch("trafilatura.fetch_url")
    def test_trafilatura_fetcher_fetch(self, mock_fetch_url, mock_traf_utils):
        """Test TrafilaturaFetcher.fetch() method."""
        from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher

        mock_fetch_url.return_value = "<html>Test</html>"
        mock_traf_utils.extract.return_value = "# Test Content"
        mock_traf_utils.extract_metadata.return_value = MagicMock(
            title="Test", author=None, date=None, description=None, fingerprint="abc"
        )

        fetcher = TrafilaturaFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success
        assert result.content == "# Test Content"
        assert result.metadata["title"] == "Test"
        mock_fetch_url.assert_called_once()

    @patch("kurt.tools.fetch.utils.trafilatura")
    @patch("kurt.tools.fetch.engines.httpx.httpx")
    def test_httpx_fetcher_fetch(self, mock_httpx, mock_traf_utils):
        """Test HttpxFetcher.fetch() method."""
        from kurt.tools.fetch.engines.httpx import HttpxFetcher

        mock_response = MagicMock()
        mock_response.text = "<html>Test</html>"
        mock_response.content = b"<html>Test</html>"
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        mock_traf_utils.extract.return_value = "# HTTPX Content"
        mock_traf_utils.extract_metadata.return_value = MagicMock(
            title="HTTPX Test", author=None, date=None, description=None, fingerprint="def"
        )

        fetcher = HttpxFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success
        assert result.content == "# HTTPX Content"
        mock_httpx.get.assert_called_once()

    def test_firecrawl_returns_error_on_missing_key(self):
        """Test that FirecrawlFetcher returns error on fetch without API key."""
        from kurt.tools.fetch.engines.firecrawl import FirecrawlFetcher

        with patch("kurt.tools.fetch.engines.firecrawl.os.getenv", return_value=None):
            # Can be instantiated without API key
            fetcher = FirecrawlFetcher()
            # But fetch returns error result
            result = fetcher.fetch("https://example.com")
            assert result.success is False
            assert "FIRECRAWL_API_KEY" in result.error

    def test_tavily_returns_error_on_missing_key(self):
        """Test that TavilyFetcher returns error on fetch without API key."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        with patch("kurt.tools.fetch.engines.tavily.os.getenv", return_value=None):
            # Can be instantiated without API key
            fetcher = TavilyFetcher()
            # But fetch returns error result
            result = fetcher.fetch("https://example.com")
            assert result.success is False
            assert "TAVILY_API_KEY" in result.error


class TestExtractWithTrafilatura:
    """Test suite for shared trafilatura extraction."""

    def test_import(self):
        """Test that utils can be imported."""
        from kurt.tools.fetch.utils import extract_with_trafilatura

        assert extract_with_trafilatura is not None

    @patch("kurt.tools.fetch.utils.trafilatura")
    def test_extracts_content_and_metadata(self, mock_trafilatura):
        """Test extraction returns content and metadata."""
        from kurt.tools.fetch.utils import extract_with_trafilatura

        mock_trafilatura.extract.return_value = "# Extracted Content"
        mock_trafilatura.extract_metadata.return_value = MagicMock(
            title="Page Title",
            author="Author Name",
            date="2024-01-01",
            description="Description",
            fingerprint="hash123",
        )

        content, metadata = extract_with_trafilatura("<html>test</html>", "https://example.com")

        assert content == "# Extracted Content"
        assert metadata["title"] == "Page Title"
        assert metadata["author"] == "Author Name"
        assert metadata["fingerprint"] == "hash123"

    @patch("kurt.tools.fetch.utils.trafilatura")
    def test_raises_on_no_content(self, mock_trafilatura):
        """Test that ValueError is raised when no content extracted."""
        from kurt.tools.fetch.utils import extract_with_trafilatura

        mock_trafilatura.extract.return_value = None
        mock_trafilatura.extract_metadata.return_value = None

        with pytest.raises(ValueError, match="No content extracted"):
            extract_with_trafilatura("<html></html>", "https://example.com")
