"""Tests for web fetch providers."""

from unittest.mock import MagicMock, patch

import pytest


class TestFetchFromWeb:
    """Test suite for fetch_from_web router."""

    def test_import(self):
        """Test that fetch_from_web can be imported."""
        from kurt.tools.fetch.web import fetch_from_web

        assert fetch_from_web is not None

    def test_empty_urls_returns_empty_dict(self):
        """Test that empty URL list returns empty dict."""
        from kurt.tools.fetch.web import fetch_from_web

        result = fetch_from_web([], "trafilatura")
        assert result == {}

    @patch("kurt.tools.fetch.utils.trafilatura")
    @patch("kurt.tools.fetch.trafilatura.trafilatura")
    def test_routes_to_trafilatura_by_default(self, mock_traf_fetch, mock_traf_utils):
        """Test that default engine uses trafilatura."""
        from kurt.tools.fetch.web import fetch_from_web

        mock_traf_fetch.fetch_url.return_value = "<html>Test</html>"
        mock_traf_utils.extract.return_value = "# Test Content"
        mock_traf_utils.extract_metadata.return_value = MagicMock(
            title="Test", author=None, date=None, description=None, fingerprint="abc"
        )

        results = fetch_from_web(["https://example.com"], "trafilatura")

        assert "https://example.com" in results
        content, metadata = results["https://example.com"]
        assert content == "# Test Content"
        assert metadata["title"] == "Test"
        mock_traf_fetch.fetch_url.assert_called_once()

    @patch("kurt.tools.fetch.utils.trafilatura")
    @patch("kurt.tools.fetch.httpx.httpx")
    def test_routes_to_httpx(self, mock_httpx, mock_traf_utils):
        """Test that httpx engine is routed correctly."""
        from kurt.tools.fetch.web import fetch_from_web

        mock_response = MagicMock()
        mock_response.text = "<html>Test</html>"
        mock_httpx.get.return_value = mock_response

        mock_traf_utils.extract.return_value = "# HTTPX Content"
        mock_traf_utils.extract_metadata.return_value = MagicMock(
            title="HTTPX Test", author=None, date=None, description=None, fingerprint="def"
        )

        results = fetch_from_web(["https://example.com"], "httpx")

        assert "https://example.com" in results
        content, metadata = results["https://example.com"]
        assert content == "# HTTPX Content"
        mock_httpx.get.assert_called_once()

    def test_firecrawl_returns_error_on_missing_key(self):
        """Test that firecrawl returns error without API key (or if not installed)."""
        from kurt.tools.fetch.web import fetch_from_web

        with patch("kurt.tools.fetch.firecrawl.os.getenv", return_value=None):
            # fetch_from_web catches exceptions and returns them in results dict
            results = fetch_from_web(["https://example.com"], "firecrawl")

            assert "https://example.com" in results
            assert isinstance(results["https://example.com"], Exception)
            # Accept either "API key not set" or "module not found" (optional dep)
            error_str = str(results["https://example.com"])
            assert "FIRECRAWL_API_KEY" in error_str or "firecrawl" in error_str.lower()

    def test_tavily_returns_error_on_missing_key(self):
        """Test that tavily returns error without API key."""
        from kurt.tools.fetch.web import fetch_from_web

        with patch("kurt.tools.fetch.tavily.os.getenv", return_value=None):
            # fetch_from_web catches exceptions and returns them in results dict
            results = fetch_from_web(["https://example.com"], "tavily")

            assert "https://example.com" in results
            assert isinstance(results["https://example.com"], Exception)
            assert "TAVILY_API_KEY" in str(results["https://example.com"])


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
