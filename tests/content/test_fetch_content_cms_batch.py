"""Tests for CMS batch fetching."""

from unittest.mock import MagicMock, patch

from kurt.content.fetch.content import fetch_batch_from_cms


class TestFetchBatchFromCMS:
    """Test batch CMS document fetching."""

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_batch_success(self, mock_get_config, mock_get_adapter):
        """Test successful batch CMS fetch."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Create mock CMS documents
        mock_doc1 = MagicMock()
        mock_doc1.id = "doc-1"
        mock_doc1.content = "# Article 1\n\nContent 1"
        mock_doc1.title = "Article 1"
        mock_doc1.author = "Author 1"
        mock_doc1.published_date = "2024-01-01"
        mock_doc1.url = "https://example.com/article-1"
        mock_doc1.metadata = {"description": "Description 1"}

        mock_doc2 = MagicMock()
        mock_doc2.id = "doc-2"
        mock_doc2.content = "# Article 2\n\nContent 2"
        mock_doc2.title = "Article 2"
        mock_doc2.author = "Author 2"
        mock_doc2.published_date = "2024-01-02"
        mock_doc2.url = "https://example.com/article-2"
        mock_doc2.metadata = {"description": "Description 2"}

        mock_adapter.fetch_batch.return_value = [mock_doc1, mock_doc2]

        # Call function
        results = fetch_batch_from_cms("sanity", "prod", ["doc-1", "doc-2"])

        # Verify
        assert len(results) == 2
        assert "doc-1" in results
        assert "doc-2" in results

        # Check doc-1 result
        content1, metadata1, url1 = results["doc-1"]
        assert content1 == "# Article 1\n\nContent 1"
        assert metadata1["title"] == "Article 1"
        assert metadata1["author"] == "Author 1"
        assert metadata1["date"] == "2024-01-01"
        assert metadata1["description"] == "Description 1"
        assert url1 == "https://example.com/article-1"

        # Check doc-2 result
        content2, metadata2, url2 = results["doc-2"]
        assert content2 == "# Article 2\n\nContent 2"
        assert metadata2["title"] == "Article 2"
        assert url2 == "https://example.com/article-2"

        # Verify adapter calls
        mock_get_config.assert_called_once_with("sanity", "prod")
        mock_get_adapter.assert_called_once_with("sanity", mock_config)
        mock_adapter.fetch_batch.assert_called_once_with(["doc-1", "doc-2"])

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_batch_with_discovery_urls(self, mock_get_config, mock_get_adapter):
        """Test batch fetch with discovery URLs provided."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Create mock CMS document without URL
        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.content = "# Content"
        mock_doc.title = "Title"
        mock_doc.author = None
        mock_doc.published_date = None
        mock_doc.url = None  # No URL from CMS
        mock_doc.metadata = None

        mock_adapter.fetch_batch.return_value = [mock_doc]

        # Call function with discovery URL
        discovery_urls = {"doc-1": "https://discovery.com/article"}
        results = fetch_batch_from_cms("sanity", "prod", ["doc-1"], discovery_urls)

        # Verify discovery URL was used
        content, metadata, url = results["doc-1"]
        assert url == "https://discovery.com/article"

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_batch_with_missing_document(self, mock_get_config, mock_get_adapter):
        """Test batch fetch when CMS doesn't return a requested document."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Return only one document when two were requested
        mock_doc1 = MagicMock()
        mock_doc1.id = "doc-1"
        mock_doc1.content = "# Content"
        mock_doc1.title = "Title"
        mock_doc1.author = None
        mock_doc1.published_date = None
        mock_doc1.url = None
        mock_doc1.metadata = None

        mock_adapter.fetch_batch.return_value = [mock_doc1]

        # Call function requesting two documents
        results = fetch_batch_from_cms("sanity", "prod", ["doc-1", "doc-2"])

        # Verify
        assert len(results) == 2

        # doc-1 should succeed
        assert not isinstance(results["doc-1"], Exception)

        # doc-2 should have exception
        assert isinstance(results["doc-2"], ValueError)
        assert "not returned from CMS batch fetch" in str(results["doc-2"])

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_batch_adapter_error(self, mock_get_config, mock_get_adapter):
        """Test batch fetch when adapter.fetch_batch() raises exception."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_adapter.fetch_batch.side_effect = Exception("CMS API Error")
        mock_get_adapter.return_value = mock_adapter

        # Call function
        results = fetch_batch_from_cms("sanity", "prod", ["doc-1", "doc-2"])

        # Verify all documents marked as failed
        assert len(results) == 2
        assert isinstance(results["doc-1"], ValueError)
        assert isinstance(results["doc-2"], ValueError)
        assert "Batch error" in str(results["doc-1"])
        assert "CMS API Error" in str(results["doc-1"])

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_batch_individual_document_error(self, mock_get_config, mock_get_adapter):
        """Test batch fetch when one document processing fails."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Create one valid document and one problematic one
        mock_doc1 = MagicMock()
        mock_doc1.id = "doc-1"
        mock_doc1.content = "# Content"
        mock_doc1.title = "Title"
        mock_doc1.author = None
        mock_doc1.published_date = None
        mock_doc1.url = None
        mock_doc1.metadata = None

        # Second document will raise error when accessing content
        mock_doc2 = MagicMock()
        mock_doc2.id = "doc-2"
        type(mock_doc2).content = property(
            lambda self: (_ for _ in ()).throw(Exception("Content error"))
        )

        mock_adapter.fetch_batch.return_value = [mock_doc1, mock_doc2]

        # Call function
        results = fetch_batch_from_cms("sanity", "prod", ["doc-1", "doc-2"])

        # Verify
        assert len(results) == 2

        # doc-1 should succeed
        assert not isinstance(results["doc-1"], Exception)

        # doc-2 should have exception
        assert isinstance(results["doc-2"], ValueError)
        assert "Failed to process" in str(results["doc-2"])

    def test_fetch_batch_empty_list(self):
        """Test batch fetch with empty document list."""
        results = fetch_batch_from_cms("sanity", "prod", [])
        assert results == {}

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_batch_metadata_without_description(self, mock_get_config, mock_get_adapter):
        """Test batch fetch with document that has no metadata dict."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Create mock document with no metadata
        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.content = "# Content"
        mock_doc.title = "Title"
        mock_doc.author = "Author"
        mock_doc.published_date = "2024-01-01"
        mock_doc.url = None
        mock_doc.metadata = None  # No metadata dict

        mock_adapter.fetch_batch.return_value = [mock_doc]

        # Call function
        results = fetch_batch_from_cms("sanity", "prod", ["doc-1"])

        # Verify metadata dict has None for description
        content, metadata, url = results["doc-1"]
        assert metadata["title"] == "Title"
        assert metadata["author"] == "Author"
        assert metadata["date"] == "2024-01-01"
        assert metadata["description"] is None

    @patch("kurt.integrations.cms.get_adapter")
    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_batch_url_priority(self, mock_get_config, mock_get_adapter):
        """Test that CMS document URL takes precedence over discovery URL."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Create mock document with URL
        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.content = "# Content"
        mock_doc.title = "Title"
        mock_doc.author = None
        mock_doc.published_date = None
        mock_doc.url = "https://cms.com/article"  # CMS has URL
        mock_doc.metadata = None

        mock_adapter.fetch_batch.return_value = [mock_doc]

        # Call function with different discovery URL
        discovery_urls = {"doc-1": "https://discovery.com/article"}
        results = fetch_batch_from_cms("sanity", "prod", ["doc-1"], discovery_urls)

        # Verify CMS URL was used (not discovery URL)
        content, metadata, url = results["doc-1"]
        assert url == "https://cms.com/article"

    @patch("kurt.integrations.cms.config.get_platform_config")
    def test_fetch_batch_config_error(self, mock_get_config):
        """Test batch fetch when platform config fails."""
        # Setup mock to raise error
        mock_get_config.side_effect = Exception("Config not found")

        # Call function
        results = fetch_batch_from_cms("invalid", "prod", ["doc-1"])

        # Verify all documents marked as failed
        assert len(results) == 1
        assert isinstance(results["doc-1"], ValueError)
        assert "Batch error" in str(results["doc-1"])
