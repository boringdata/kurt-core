"""
Unit tests for CMS fetch utility.

Tests fetch_from_cms and fetch_batch_from_cms functions with mocked CMS adapters.
"""

from unittest.mock import MagicMock, patch

import pytest

from kurt.content.ingestion.utils.cms import fetch_batch_from_cms, fetch_from_cms


class TestFetchFromCms:
    """Tests for fetch_from_cms function."""

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_cms_document_success(self, mock_config, mock_get_adapter):
        """Test successfully fetching a CMS document."""
        # Setup mock adapter
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        mock_cms_doc = MagicMock()
        mock_cms_doc.content = "# Blog Post\n\nContent here"
        mock_cms_doc.title = "Blog Post"
        mock_cms_doc.author = "Jane Doe"
        mock_cms_doc.published_date = "2024-01-15"
        mock_cms_doc.url = "https://blog.example.com/posts/my-post"
        mock_cms_doc.metadata = {"description": "A blog post"}
        mock_adapter.fetch.return_value = mock_cms_doc

        content, metadata, public_url = fetch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_id="post-123",
            discovery_url="https://blog.example.com",
        )

        assert content == "# Blog Post\n\nContent here"
        assert metadata["title"] == "Blog Post"
        assert metadata["author"] == "Jane Doe"
        assert public_url == "https://blog.example.com/posts/my-post"

        mock_adapter.fetch.assert_called_once_with("post-123")

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_cms_uses_discovery_url_as_fallback(self, mock_config, mock_get_adapter):
        """Test that discovery_url is used when CMS doc has no url."""
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        mock_cms_doc = MagicMock()
        mock_cms_doc.content = "Content"
        mock_cms_doc.title = "Title"
        mock_cms_doc.author = None
        mock_cms_doc.published_date = None
        mock_cms_doc.url = None  # No URL from CMS
        mock_cms_doc.metadata = None
        mock_adapter.fetch.return_value = mock_cms_doc

        content, metadata, public_url = fetch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_id="post-123",
            discovery_url="https://fallback.com/page",
        )

        # Should use discovery_url as fallback
        assert public_url == "https://fallback.com/page"

    def test_fetch_cms_requires_document_id(self):
        """Test that cms_document_id is required."""
        with pytest.raises(ValueError, match="cms_document_id is required"):
            fetch_from_cms(
                platform="sanity",
                instance="prod",
                cms_document_id=None,
            )

    def test_fetch_cms_requires_document_id_empty_string(self):
        """Test that empty cms_document_id raises error."""
        with pytest.raises(ValueError, match="cms_document_id is required"):
            fetch_from_cms(
                platform="sanity",
                instance="prod",
                cms_document_id="",
            )

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_cms_handles_adapter_error(self, mock_config, mock_get_adapter):
        """Test that adapter errors are wrapped in ValueError."""
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.fetch.side_effect = Exception("CMS API error")

        with pytest.raises(ValueError, match="Failed to fetch from sanity/prod"):
            fetch_from_cms(
                platform="sanity",
                instance="prod",
                cms_document_id="post-123",
            )


class TestFetchBatchFromCms:
    """Tests for fetch_batch_from_cms function."""

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_batch_fetch_success(self, mock_config, mock_get_adapter):
        """Test successfully batch fetching CMS documents."""
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Create mock CMS documents
        mock_doc1 = MagicMock()
        mock_doc1.id = "doc1"
        mock_doc1.content = "# Doc 1"
        mock_doc1.title = "Document 1"
        mock_doc1.author = "Author 1"
        mock_doc1.published_date = "2024-01-01"
        mock_doc1.url = "https://example.com/doc1"
        mock_doc1.metadata = {}

        mock_doc2 = MagicMock()
        mock_doc2.id = "doc2"
        mock_doc2.content = "# Doc 2"
        mock_doc2.title = "Document 2"
        mock_doc2.author = "Author 2"
        mock_doc2.published_date = "2024-01-02"
        mock_doc2.url = "https://example.com/doc2"
        mock_doc2.metadata = {}

        mock_adapter.fetch_batch.return_value = [mock_doc1, mock_doc2]

        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc1", "doc2"],
        )

        assert len(results) == 2
        assert results["doc1"][0] == "# Doc 1"
        assert results["doc1"][1]["title"] == "Document 1"
        assert results["doc2"][0] == "# Doc 2"

    def test_batch_fetch_empty_list(self):
        """Test batch fetch with empty document list."""
        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=[],
        )

        assert results == {}

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_batch_fetch_uses_discovery_urls(self, mock_config, mock_get_adapter):
        """Test that discovery_urls dict is used for public URLs."""
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        mock_doc = MagicMock()
        mock_doc.id = "doc1"
        mock_doc.content = "Content"
        mock_doc.title = "Title"
        mock_doc.author = None
        mock_doc.published_date = None
        mock_doc.url = None  # No URL from CMS
        mock_doc.metadata = None
        mock_adapter.fetch_batch.return_value = [mock_doc]

        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc1"],
            discovery_urls={"doc1": "https://custom.com/doc1"},
        )

        # Should use discovery_url
        assert results["doc1"][2] == "https://custom.com/doc1"

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_batch_fetch_handles_missing_documents(self, mock_config, mock_get_adapter):
        """Test batch fetch when some documents not returned."""
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        mock_doc = MagicMock()
        mock_doc.id = "doc1"
        mock_doc.content = "Content"
        mock_doc.title = "Title"
        mock_doc.author = None
        mock_doc.published_date = None
        mock_doc.url = None
        mock_doc.metadata = None

        # Only return doc1, not doc2
        mock_adapter.fetch_batch.return_value = [mock_doc]

        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc1", "doc2"],
        )

        # doc1 should succeed
        assert not isinstance(results["doc1"], Exception)
        # doc2 should be an error
        assert isinstance(results["doc2"], Exception)
        assert "not returned" in str(results["doc2"])

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_batch_fetch_handles_batch_error(self, mock_config, mock_get_adapter):
        """Test batch fetch when batch API fails."""
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.fetch_batch.side_effect = Exception("Batch API error")

        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc1", "doc2"],
        )

        # All docs should be errors
        assert isinstance(results["doc1"], Exception)
        assert isinstance(results["doc2"], Exception)
        assert "Batch error" in str(results["doc1"])
