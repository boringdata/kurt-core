"""Tests for web fetch providers."""

from unittest.mock import MagicMock, patch

import pytest


class TestFetchFromWeb:
    """Test suite for fetch_from_web router."""

    def test_import(self):
        """Test that fetch_from_web can be imported."""
        from kurt_new.workflows.fetch.fetch_web import fetch_from_web

        assert fetch_from_web is not None

    @patch("kurt_new.workflows.fetch.utils.trafilatura")
    @patch("kurt_new.workflows.fetch.fetch_trafilatura.trafilatura")
    def test_routes_to_trafilatura_by_default(self, mock_traf_fetch, mock_traf_utils):
        """Test that default engine uses trafilatura."""
        from kurt_new.workflows.fetch.fetch_web import fetch_from_web

        mock_traf_fetch.fetch_url.return_value = "<html>Test</html>"
        mock_traf_utils.extract.return_value = "# Test Content"
        mock_traf_utils.extract_metadata.return_value = MagicMock(
            title="Test", author=None, date=None, description=None, fingerprint="abc"
        )

        content, metadata = fetch_from_web("https://example.com", "trafilatura")

        assert content == "# Test Content"
        assert metadata["title"] == "Test"
        mock_traf_fetch.fetch_url.assert_called_once()

    @patch("kurt_new.workflows.fetch.utils.trafilatura")
    @patch("kurt_new.workflows.fetch.fetch_httpx.httpx")
    def test_routes_to_httpx(self, mock_httpx, mock_traf_utils):
        """Test that httpx engine is routed correctly."""
        from kurt_new.workflows.fetch.fetch_web import fetch_from_web

        mock_response = MagicMock()
        mock_response.text = "<html>Test</html>"
        mock_httpx.get.return_value = mock_response

        mock_traf_utils.extract.return_value = "# HTTPX Content"
        mock_traf_utils.extract_metadata.return_value = MagicMock(
            title="HTTPX Test", author=None, date=None, description=None, fingerprint="def"
        )

        content, metadata = fetch_from_web("https://example.com", "httpx")

        assert content == "# HTTPX Content"
        mock_httpx.get.assert_called_once()

    @patch("kurt_new.workflows.fetch.fetch_firecrawl.os.getenv")
    def test_firecrawl_requires_api_key(self, mock_getenv):
        """Test that firecrawl raises error without API key."""
        from kurt_new.workflows.fetch.fetch_web import fetch_from_web

        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="FIRECRAWL_API_KEY"):
            fetch_from_web("https://example.com", "firecrawl")


class TestExtractWithTrafilatura:
    """Test suite for shared trafilatura extraction."""

    def test_import(self):
        """Test that utils can be imported."""
        from kurt_new.workflows.fetch.utils import extract_with_trafilatura

        assert extract_with_trafilatura is not None

    @patch("kurt_new.workflows.fetch.utils.trafilatura")
    def test_extracts_content_and_metadata(self, mock_trafilatura):
        """Test extraction returns content and metadata."""
        from kurt_new.workflows.fetch.utils import extract_with_trafilatura

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

    @patch("kurt_new.workflows.fetch.utils.trafilatura")
    def test_raises_on_no_content(self, mock_trafilatura):
        """Test that ValueError is raised when no content extracted."""
        from kurt_new.workflows.fetch.utils import extract_with_trafilatura

        mock_trafilatura.extract.return_value = None
        mock_trafilatura.extract_metadata.return_value = None

        with pytest.raises(ValueError, match="No content extracted"):
            extract_with_trafilatura("<html></html>", "https://example.com")
