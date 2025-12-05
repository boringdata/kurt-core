"""Tests for batch_fetch_content_step function."""

from unittest.mock import patch

from kurt.content.fetch.workflow import batch_fetch_content_step


class TestBatchFetchContentStep:
    """Test the batch_fetch_content_step function."""

    @patch("kurt.content.fetch.workflow.fetch_batch_from_cms")
    @patch("kurt.content.fetch.workflow.fetch_with_firecrawl")
    @patch("kurt.content.fetch.workflow._get_fetch_engine")
    def test_batch_fetch_with_firecrawl(
        self, mock_get_engine, mock_fetch_firecrawl, mock_fetch_cms
    ):
        """Test batch fetching with Firecrawl engine for multiple web docs."""
        # Setup
        mock_get_engine.return_value = "firecrawl"
        mock_fetch_firecrawl.return_value = {
            "https://example.com/1": ("# Content 1", {"title": "Page 1"}),
            "https://example.com/2": ("# Content 2", {"title": "Page 2"}),
        }

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "https://example.com/1",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
            {
                "id": "doc2",
                "source_url": "https://example.com/2",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos, fetch_engine="firecrawl")

        # Verify
        assert len(results) == 2
        assert results["doc1"]["content"] == "# Content 1"
        assert results["doc1"]["metadata"]["title"] == "Page 1"
        assert results["doc2"]["content"] == "# Content 2"
        assert results["doc2"]["metadata"]["title"] == "Page 2"

        # Should have called Firecrawl batch API
        mock_fetch_firecrawl.assert_called_once_with(
            ["https://example.com/1", "https://example.com/2"]
        )
        mock_fetch_cms.assert_not_called()

    @patch("kurt.content.fetch.workflow.fetch_batch_from_cms")
    @patch("kurt.content.fetch.workflow.fetch_with_firecrawl")
    @patch("kurt.content.fetch.workflow._get_fetch_engine")
    def test_batch_fetch_with_cms_documents(
        self, mock_get_engine, mock_fetch_firecrawl, mock_fetch_cms
    ):
        """Test batch fetching with CMS documents."""
        # Setup
        mock_get_engine.return_value = "firecrawl"
        mock_fetch_cms.return_value = {
            "article1": ("# CMS Content 1", {"title": "Article 1"}, "https://site.com/article1"),
            "article2": ("# CMS Content 2", {"title": "Article 2"}, "https://site.com/article2"),
        }

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "sanity/prod/article1",
                "cms_platform": "sanity",
                "cms_instance": "prod",
                "cms_document_id": "article1",
                "discovery_url": "https://site.com/article1",
            },
            {
                "id": "doc2",
                "source_url": "sanity/prod/article2",
                "cms_platform": "sanity",
                "cms_instance": "prod",
                "cms_document_id": "article2",
                "discovery_url": "https://site.com/article2",
            },
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos, fetch_engine="firecrawl")

        # Verify
        assert len(results) == 2
        assert results["doc1"]["content"] == "# CMS Content 1"
        assert results["doc1"]["metadata"]["title"] == "Article 1"
        assert results["doc1"]["public_url"] == "https://site.com/article1"
        assert results["doc2"]["content"] == "# CMS Content 2"
        assert results["doc2"]["metadata"]["title"] == "Article 2"

        # Should have called CMS batch API
        mock_fetch_cms.assert_called_once_with(
            "sanity",
            "prod",
            ["article1", "article2"],
            {"article1": "https://site.com/article1", "article2": "https://site.com/article2"},
        )
        mock_fetch_firecrawl.assert_not_called()

    @patch("kurt.content.fetch.workflow.fetch_batch_from_cms")
    @patch("kurt.content.fetch.workflow.fetch_with_firecrawl")
    @patch("kurt.content.fetch.workflow._get_fetch_engine")
    def test_batch_fetch_mixed_sources_with_batch_web(
        self, mock_get_engine, mock_fetch_firecrawl, mock_fetch_cms
    ):
        """Test batch fetching with mixed CMS and multiple web documents using batch API."""
        # Setup
        mock_get_engine.return_value = "firecrawl"
        mock_fetch_cms.return_value = {
            "article1": ("# CMS Content", {"title": "Article"}, "https://site.com/article"),
        }
        mock_fetch_firecrawl.return_value = {
            "https://example.com/1": ("# Web 1", {"title": "Page 1"}),
            "https://example.com/2": ("# Web 2", {"title": "Page 2"}),
        }

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "sanity/prod/article1",
                "cms_platform": "sanity",
                "cms_instance": "prod",
                "cms_document_id": "article1",
            },
            {
                "id": "doc2",
                "source_url": "https://example.com/1",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
            {
                "id": "doc3",
                "source_url": "https://example.com/2",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos, fetch_engine="firecrawl")

        # Verify
        assert len(results) == 3
        assert results["doc1"]["content"] == "# CMS Content"
        assert results["doc2"]["content"] == "# Web 1"
        assert results["doc3"]["content"] == "# Web 2"

        # Both batch APIs should be called
        mock_fetch_cms.assert_called_once()
        mock_fetch_firecrawl.assert_called_once_with(
            ["https://example.com/1", "https://example.com/2"]
        )

    @patch("kurt.content.fetch.workflow.fetch_batch_from_cms")
    @patch("kurt.content.fetch.workflow.fetch_with_firecrawl")
    @patch("kurt.content.fetch.workflow.fetch_from_web")
    @patch("kurt.content.fetch.workflow._get_fetch_engine")
    def test_batch_fetch_mixed_sources_single_web(
        self, mock_get_engine, mock_fetch_web, mock_fetch_firecrawl, mock_fetch_cms
    ):
        """Test batch fetching with mixed CMS and single web document (no batch for web)."""
        # Setup
        mock_get_engine.return_value = "firecrawl"
        mock_fetch_cms.return_value = {
            "article1": ("# CMS Content", {"title": "Article"}, "https://site.com/article"),
        }
        # Single web doc won't use batch API, will use fetch_from_web
        mock_fetch_web.return_value = ("# Web Content", {"title": "Web Page"})

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "sanity/prod/article1",
                "cms_platform": "sanity",
                "cms_instance": "prod",
                "cms_document_id": "article1",
            },
            {
                "id": "doc2",
                "source_url": "https://example.com",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos, fetch_engine="firecrawl")

        # Verify
        assert len(results) == 2
        assert results["doc1"]["content"] == "# CMS Content"
        assert results["doc2"]["content"] == "# Web Content"

        # CMS batch should be called, but single web doc uses fetch_from_web
        mock_fetch_cms.assert_called_once()
        mock_fetch_web.assert_called_once_with("https://example.com", "firecrawl")
        mock_fetch_firecrawl.assert_not_called()  # Not called for single URL

    @patch("kurt.content.fetch.workflow.fetch_with_firecrawl")
    @patch("kurt.content.fetch.workflow._get_fetch_engine")
    def test_batch_fetch_with_errors(self, mock_get_engine, mock_fetch_firecrawl):
        """Test batch fetching with some URLs failing."""
        # Setup
        mock_get_engine.return_value = "firecrawl"
        mock_fetch_firecrawl.return_value = {
            "https://example.com/1": ("# Content", {"title": "Success"}),
            "https://example.com/2": ValueError("Failed to fetch"),
        }

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "https://example.com/1",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
            {
                "id": "doc2",
                "source_url": "https://example.com/2",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos)

        # Verify
        assert len(results) == 2
        assert results["doc1"]["content"] == "# Content"
        assert "error" in results["doc2"]
        assert "Failed to fetch" in str(results["doc2"]["error"])

    @patch("kurt.content.fetch.workflow.fetch_from_web")
    @patch("kurt.content.fetch.workflow._get_fetch_engine")
    def test_batch_fetch_fallback_to_individual(self, mock_get_engine, mock_fetch_web):
        """Test batch fetching falls back to individual fetches for non-Firecrawl engines."""
        # Setup
        mock_get_engine.return_value = "trafilatura"
        mock_fetch_web.side_effect = [
            ("# Content 1", {"title": "Page 1"}),
            ("# Content 2", {"title": "Page 2"}),
        ]

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "https://example.com/1",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
            {
                "id": "doc2",
                "source_url": "https://example.com/2",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            },
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos)

        # Verify
        assert len(results) == 2
        assert results["doc1"]["content"] == "# Content 1"
        assert results["doc2"]["content"] == "# Content 2"

        # Should call individual fetch for each URL
        assert mock_fetch_web.call_count == 2

    @patch("kurt.content.fetch.workflow.fetch_from_web")
    @patch("kurt.content.fetch.workflow.fetch_with_firecrawl")
    @patch("kurt.content.fetch.workflow._get_fetch_engine")
    def test_batch_fetch_single_url_no_batch(
        self, mock_get_engine, mock_fetch_firecrawl, mock_fetch_web
    ):
        """Test that single URL doesn't use batch API."""
        # Setup
        mock_get_engine.return_value = "firecrawl"
        mock_fetch_web.return_value = ("# Content", {"title": "Page"})

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "https://example.com",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
            }
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos)

        # Verify - should use fetch_from_web for single URL, not batch API
        assert len(results) == 1
        assert results["doc1"]["content"] == "# Content"
        mock_fetch_web.assert_called_once_with("https://example.com", "firecrawl")
        mock_fetch_firecrawl.assert_not_called()

    @patch("kurt.content.fetch.workflow.fetch_batch_from_cms")
    def test_batch_fetch_cms_batch_error(self, mock_fetch_cms):
        """Test handling of CMS batch API errors."""
        # Setup
        mock_fetch_cms.side_effect = Exception("CMS API Error")

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "sanity/prod/article1",
                "cms_platform": "sanity",
                "cms_instance": "prod",
                "cms_document_id": "article1",
            },
            {
                "id": "doc2",
                "source_url": "sanity/prod/article2",
                "cms_platform": "sanity",
                "cms_instance": "prod",
                "cms_document_id": "article2",
            },
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos)

        # Verify - all docs should have errors
        assert len(results) == 2
        assert "error" in results["doc1"]
        assert "error" in results["doc2"]
        assert "CMS API Error" in str(results["doc1"]["error"])

    def test_batch_fetch_empty_list(self):
        """Test batch fetching with empty document list."""
        results = batch_fetch_content_step([])
        assert results == {}

    @patch("kurt.content.fetch.workflow.fetch_batch_from_cms")
    def test_batch_fetch_multiple_cms_instances(self, mock_fetch_cms):
        """Test batch fetching groups CMS documents by platform/instance."""
        # Setup
        mock_fetch_cms.side_effect = [
            {"article1": ("# Content 1", {"title": "1"}, "url1")},
            {"article2": ("# Content 2", {"title": "2"}, "url2")},
        ]

        doc_infos = [
            {
                "id": "doc1",
                "source_url": "sanity/prod/article1",
                "cms_platform": "sanity",
                "cms_instance": "prod",
                "cms_document_id": "article1",
            },
            {
                "id": "doc2",
                "source_url": "sanity/staging/article2",
                "cms_platform": "sanity",
                "cms_instance": "staging",
                "cms_document_id": "article2",
            },
        ]

        # Execute
        results = batch_fetch_content_step(doc_infos)

        # Verify - should make separate calls per instance
        assert mock_fetch_cms.call_count == 2
        assert len(results) == 2
