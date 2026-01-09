"""Tests for CMS fetch business logic."""

from unittest.mock import MagicMock, patch

import pytest

from kurt.integrations.cms.fetch import (
    _build_metadata_dict,
    fetch_batch_from_cms,
    fetch_from_cms,
)


class TestBuildMetadataDict:
    """Test _build_metadata_dict helper function."""

    def test_all_fields(self):
        """Test building metadata with all fields."""
        result = _build_metadata_dict(
            title="My Article",
            author="Jane Doe",
            date="2024-01-15",
            description="Article description",
        )

        assert result == {
            "title": "My Article",
            "author": "Jane Doe",
            "date": "2024-01-15",
            "description": "Article description",
        }

    def test_partial_fields(self):
        """Test building metadata with some fields."""
        result = _build_metadata_dict(title="My Article")

        assert result == {
            "title": "My Article",
            "author": None,
            "date": None,
            "description": None,
        }

    def test_no_fields(self):
        """Test building metadata with no fields."""
        result = _build_metadata_dict()

        assert result == {
            "title": None,
            "author": None,
            "date": None,
            "description": None,
        }


class TestFetchFromCMS:
    """Test fetch_from_cms function."""

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_successful_fetch(self, mock_get_config, mock_get_adapter):
        """Test successful document fetch."""
        # Setup mock adapter
        mock_adapter = MagicMock()
        mock_document = MagicMock()
        mock_document.content = "# Article Title\n\nContent here."
        mock_document.title = "Article Title"
        mock_document.author = "Jane Doe"
        mock_document.published_date = "2024-01-15"
        mock_document.url = "https://example.com/article"
        mock_document.metadata = {"description": "Test description"}

        mock_adapter.fetch.return_value = mock_document
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {"project_id": "test"}

        # Execute
        content, metadata, url = fetch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_id="doc-123",
        )

        # Verify
        assert content == "# Article Title\n\nContent here."
        assert metadata["title"] == "Article Title"
        assert metadata["author"] == "Jane Doe"
        assert metadata["date"] == "2024-01-15"
        assert metadata["description"] == "Test description"
        assert url == "https://example.com/article"

        mock_adapter.fetch.assert_called_once_with("doc-123")

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_uses_discovery_url_when_no_cms_url(self, mock_get_config, mock_get_adapter):
        """Test falls back to discovery_url when CMS document has no URL."""
        mock_adapter = MagicMock()
        mock_document = MagicMock()
        mock_document.content = "Content"
        mock_document.title = "Title"
        mock_document.author = None
        mock_document.published_date = None
        mock_document.url = None  # No URL from CMS
        mock_document.metadata = {}

        mock_adapter.fetch.return_value = mock_document
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {}

        content, metadata, url = fetch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_id="doc-123",
            discovery_url="https://discovered.example.com/article",
        )

        assert url == "https://discovered.example.com/article"

    def test_missing_cms_document_id_raises(self):
        """Test that missing cms_document_id raises ValueError."""
        with pytest.raises(ValueError, match="cms_document_id is required"):
            fetch_from_cms(
                platform="sanity",
                instance="prod",
                cms_document_id="",
            )

    def test_none_cms_document_id_raises(self):
        """Test that None cms_document_id raises ValueError."""
        with pytest.raises(ValueError, match="cms_document_id is required"):
            fetch_from_cms(
                platform="sanity",
                instance="prod",
                cms_document_id=None,
            )

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_adapter_error_wrapped(self, mock_get_config, mock_get_adapter):
        """Test that adapter errors are wrapped with context."""
        mock_adapter = MagicMock()
        mock_adapter.fetch.side_effect = Exception("Connection timeout")
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {}

        with pytest.raises(ValueError, match="Failed to fetch from sanity/prod"):
            fetch_from_cms(
                platform="sanity",
                instance="prod",
                cms_document_id="doc-123",
            )

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_metadata_without_description(self, mock_get_config, mock_get_adapter):
        """Test handling document with no metadata description."""
        mock_adapter = MagicMock()
        mock_document = MagicMock()
        mock_document.content = "Content"
        mock_document.title = "Title"
        mock_document.author = None
        mock_document.published_date = None
        mock_document.url = None
        mock_document.metadata = None  # No metadata at all

        mock_adapter.fetch.return_value = mock_document
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {}

        content, metadata, url = fetch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_id="doc-123",
        )

        assert metadata["description"] is None


class TestFetchBatchFromCMS:
    """Test fetch_batch_from_cms function."""

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_successful_batch_fetch(self, mock_get_config, mock_get_adapter):
        """Test successful batch document fetch."""
        # Setup mock adapter
        mock_adapter = MagicMock()

        mock_doc1 = MagicMock()
        mock_doc1.id = "doc-1"
        mock_doc1.content = "Content 1"
        mock_doc1.title = "Title 1"
        mock_doc1.author = "Author 1"
        mock_doc1.published_date = "2024-01-01"
        mock_doc1.url = "https://example.com/doc-1"
        mock_doc1.metadata = {"description": "Desc 1"}

        mock_doc2 = MagicMock()
        mock_doc2.id = "doc-2"
        mock_doc2.content = "Content 2"
        mock_doc2.title = "Title 2"
        mock_doc2.author = None
        mock_doc2.published_date = None
        mock_doc2.url = None
        mock_doc2.metadata = {}

        mock_adapter.fetch_batch.return_value = [mock_doc1, mock_doc2]
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {}

        # Execute
        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc-1", "doc-2"],
            discovery_urls={"doc-2": "https://discovered.example.com/doc-2"},
        )

        # Verify doc-1
        assert "doc-1" in results
        content1, metadata1, url1 = results["doc-1"]
        assert content1 == "Content 1"
        assert metadata1["title"] == "Title 1"
        assert url1 == "https://example.com/doc-1"

        # Verify doc-2 uses discovery URL
        assert "doc-2" in results
        content2, metadata2, url2 = results["doc-2"]
        assert content2 == "Content 2"
        assert url2 == "https://discovered.example.com/doc-2"

    def test_empty_document_ids_returns_empty(self):
        """Test empty document IDs returns empty dict."""
        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=[],
        )

        assert results == {}

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_missing_document_in_batch(self, mock_get_config, mock_get_adapter):
        """Test handling when batch fetch doesn't return all documents."""
        mock_adapter = MagicMock()

        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.content = "Content"
        mock_doc.title = "Title"
        mock_doc.author = None
        mock_doc.published_date = None
        mock_doc.url = None
        mock_doc.metadata = {}

        # Only return doc-1, not doc-2
        mock_adapter.fetch_batch.return_value = [mock_doc]
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {}

        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc-1", "doc-2"],
        )

        # doc-1 should succeed
        assert not isinstance(results["doc-1"], Exception)

        # doc-2 should be an error
        assert isinstance(results["doc-2"], Exception)
        assert "not returned from CMS batch fetch" in str(results["doc-2"])

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_batch_fetch_total_failure(self, mock_get_config, mock_get_adapter):
        """Test handling when batch fetch fails entirely."""
        mock_adapter = MagicMock()
        mock_adapter.fetch_batch.side_effect = Exception("API unavailable")
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {}

        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc-1", "doc-2"],
        )

        # All documents should be errors
        assert isinstance(results["doc-1"], Exception)
        assert isinstance(results["doc-2"], Exception)
        assert "Batch error" in str(results["doc-1"])

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_batch_partial_processing_error(self, mock_get_config, mock_get_adapter):
        """Test handling when individual document processing fails."""
        mock_adapter = MagicMock()

        mock_doc1 = MagicMock()
        mock_doc1.id = "doc-1"
        mock_doc1.content = "Content"
        mock_doc1.title = "Title"
        mock_doc1.author = None
        mock_doc1.published_date = None
        mock_doc1.url = None
        mock_doc1.metadata = None  # This could cause issues in processing

        mock_adapter.fetch_batch.return_value = [mock_doc1]
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {}

        # Should not raise, should return results dict
        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc-1"],
        )

        assert "doc-1" in results

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_batch_with_no_discovery_urls(self, mock_get_config, mock_get_adapter):
        """Test batch fetch works without discovery_urls parameter."""
        mock_adapter = MagicMock()

        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.content = "Content"
        mock_doc.title = "Title"
        mock_doc.author = None
        mock_doc.published_date = None
        mock_doc.url = "https://from-cms.example.com"
        mock_doc.metadata = {}

        mock_adapter.fetch_batch.return_value = [mock_doc]
        mock_get_adapter.return_value = mock_adapter
        mock_get_config.return_value = {}

        results = fetch_batch_from_cms(
            platform="sanity",
            instance="prod",
            cms_document_ids=["doc-1"],
            # No discovery_urls provided
        )

        content, metadata, url = results["doc-1"]
        assert url == "https://from-cms.example.com"
