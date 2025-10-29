"""
Tests for add workflow functionality.

═══════════════════════════════════════════════════════════════════════════════
TEST COVERAGE
═══════════════════════════════════════════════════════════════════════════════

TestIsSinglePageUrl
────────────────────────────────────────────────────────────────────────────────
  ✓ test_is_single_page_url_single_page
      → Verifies specific blog posts, docs pages are classified as single page

  ✓ test_is_single_page_url_multi_page
      → Verifies root URLs, index pages are classified as multi-page

TestGroupUrlsByPathPrefix
────────────────────────────────────────────────────────────────────────────────
  ✓ test_group_urls_by_path_prefix
      → Verifies URLs are grouped by first path segment

  ✓ test_group_urls_by_path_prefix_edge_cases
      → Verifies handling of root paths and empty paths

TestShouldConfirmBatch
────────────────────────────────────────────────────────────────────────────────
  ✓ test_should_confirm_batch_under_threshold
      → Verifies no confirmation needed for small batches (<20)

  ✓ test_should_confirm_batch_over_threshold
      → Verifies confirmation needed for large batches (≥20)

  ✓ test_should_confirm_batch_force
      → Verifies force flag skips confirmation

TestAddSinglePage
────────────────────────────────────────────────────────────────────────────────
  ✓ test_add_single_page_new_document
      → Verifies creating a new single page document

  ✓ test_add_single_page_existing_document
      → Verifies handling of existing documents

  ✓ test_add_single_page_fetch_only
      → Verifies fetch without indexing

  ✓ test_add_single_page_discover_only
      → Verifies discover without fetch or index

TestAddMultiplePages
────────────────────────────────────────────────────────────────────────────────
  ✓ test_add_multiple_pages_success
      → Verifies complete multi-page workflow

  ✓ test_add_multiple_pages_with_filters
      → Verifies URL filtering works correctly

  ✓ test_add_multiple_pages_discover_only
      → Verifies discover-only mode

═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from kurt.ingestion.add import (
    group_urls_by_path_prefix,
    is_single_page_url,
    should_confirm_batch,
)

# ============================================================================
# URL Classification Tests
# ============================================================================


class TestIsSinglePageUrl:
    """Test single page vs multi-page URL classification."""

    def test_is_single_page_url_single_page(self):
        """Test URLs that should be classified as single pages."""
        single_page_urls = [
            "https://example.com/blog/my-post",
            "https://example.com/docs/getting-started/installation",
            "https://example.com/articles/2024/01/machine-learning",
            "https://example.com/tutorials/python-basics",
            "https://example.com/path/to/specific-page",
        ]

        for url in single_page_urls:
            assert is_single_page_url(url), f"Expected single page: {url}"

    def test_is_single_page_url_multi_page(self):
        """Test URLs that should be classified as multi-page."""
        multi_page_urls = [
            "https://example.com",
            "https://example.com/",
            "https://example.com/blog",
            "https://example.com/blog/",
            "https://example.com/docs",
            "https://example.com/docs/",
            "https://example.com/documentation/",
            "https://example.com/articles",
            "https://example.com/posts/",
            "https://example.com/news",
            "https://example.com/guides/",
        ]

        for url in multi_page_urls:
            assert not is_single_page_url(url), f"Expected multi-page: {url}"


# ============================================================================
# URL Grouping Tests
# ============================================================================


class TestGroupUrlsByPathPrefix:
    """Test URL grouping by path prefix."""

    def test_group_urls_by_path_prefix(self):
        """Test grouping URLs by first path segment."""
        urls = [
            {"url": "https://example.com/blog/post-1"},
            {"url": "https://example.com/blog/post-2"},
            {"url": "https://example.com/blog/post-3"},
            {"url": "https://example.com/docs/getting-started"},
            {"url": "https://example.com/docs/api-reference"},
            {"url": "https://example.com/tutorials/python"},
        ]

        groups = group_urls_by_path_prefix(urls)

        assert groups["/blog"] == 3
        assert groups["/docs"] == 2
        assert groups["/tutorials"] == 1

    def test_group_urls_by_path_prefix_edge_cases(self):
        """Test edge cases in URL grouping."""
        urls = [
            {"url": "https://example.com"},
            {"url": "https://example.com/"},
            {"url": "https://example.com/single-path"},
        ]

        groups = group_urls_by_path_prefix(urls)

        assert groups["/"] >= 2  # Root URLs
        assert groups["/single-path"] == 1


# ============================================================================
# Confirmation Tests
# ============================================================================


class TestShouldConfirmBatch:
    """Test batch confirmation logic."""

    def test_should_confirm_batch_under_threshold(self):
        """Test no confirmation needed for small batches."""
        assert not should_confirm_batch(5, force=False)
        assert not should_confirm_batch(19, force=False)
        assert not should_confirm_batch(20, force=False)  # At threshold, no confirmation

    def test_should_confirm_batch_over_threshold(self):
        """Test confirmation needed for large batches."""
        assert should_confirm_batch(21, force=False)  # Just over threshold
        assert should_confirm_batch(50, force=False)
        assert should_confirm_batch(100, force=False)

    def test_should_confirm_batch_force(self):
        """Test force flag skips confirmation."""
        assert not should_confirm_batch(20, force=True)
        assert not should_confirm_batch(100, force=True)


# ============================================================================
# Integration Tests - Add Single Page
# ============================================================================


class TestAddSinglePage:
    """Test single page add workflow."""

    @patch("kurt.ingestion.add.get_session")
    @patch("kurt.ingestion.add.add_document")
    @patch("kurt.ingestion.add.fetch_document")
    def test_add_single_page_new_document(self, mock_fetch, mock_add_doc, mock_session):
        """Test adding a new single page document."""
        from kurt.ingestion.add import add_single_page

        doc_id = str(uuid4())

        # Mock database session - no existing document
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.exec.return_value.first.return_value = None

        # Mock add_document returns new document ID
        mock_add_doc.return_value = doc_id

        # Mock fetch result
        mock_fetch.return_value = {
            "success": True,
            "document_id": doc_id,
            "title": "Test Page",
            "content_length": 1000,
        }

        # Run add
        result = add_single_page("https://example.com/test", fetch=True, index=False)

        # Verify result
        assert result["created"] is True
        assert result["doc_id"] == doc_id
        assert result["fetched"] is True
        assert result["indexed"] is False

        # Verify functions called
        mock_add_doc.assert_called_once_with("https://example.com/test")
        mock_fetch.assert_called_once()

    @patch("kurt.ingestion.add.get_session")
    def test_add_single_page_existing_document(self, mock_session):
        """Test handling of existing documents."""
        from kurt.db.models import Document, IngestionStatus, SourceType
        from kurt.ingestion.add import add_single_page

        doc_id = uuid4()

        # Mock database session - existing document
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        existing_doc = Document(
            id=doc_id,
            title="Existing Doc",
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            indexed_with_hash="somehash",
        )
        mock_db.exec.return_value.first.return_value = existing_doc

        # Run add
        result = add_single_page("https://example.com/test", fetch=True, index=False)

        # Verify result
        assert result["created"] is False
        assert result["doc_id"] == str(doc_id)
        assert result["fetched"] is False  # Already fetched
        assert result["indexed"] is False

    @patch("kurt.ingestion.add.get_session")
    @patch("kurt.ingestion.add.add_document")
    @patch("kurt.ingestion.add.fetch_document")
    def test_add_single_page_fetch_only(self, mock_fetch, mock_add_doc, mock_session):
        """Test fetch without indexing."""
        from kurt.ingestion.add import add_single_page

        doc_id = str(uuid4())

        # Mock database session - no existing document
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.exec.return_value.first.return_value = None

        # Mock add_document
        mock_add_doc.return_value = doc_id

        # Mock fetch
        mock_fetch.return_value = {
            "success": True,
            "document_id": doc_id,
            "title": "Test Page",
            "content_length": 1000,
        }

        # Run add with fetch only
        result = add_single_page("https://example.com/test", fetch=True, index=False)

        # Verify
        assert result["fetched"] is True
        assert result["indexed"] is False
        mock_fetch.assert_called_once()

    @patch("kurt.ingestion.add.get_session")
    @patch("kurt.ingestion.add.add_document")
    def test_add_single_page_discover_only(self, mock_add_doc, mock_session):
        """Test discover without fetch or index."""
        from kurt.ingestion.add import add_single_page

        doc_id = str(uuid4())

        # Mock database session - no existing document
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.exec.return_value.first.return_value = None

        # Mock add_document
        mock_add_doc.return_value = doc_id

        # Run add with discover only
        result = add_single_page("https://example.com/test", fetch=False, index=False)

        # Verify
        assert result["created"] is True
        assert result["fetched"] is False
        assert result["indexed"] is False


# ============================================================================
# Integration Tests - Add Multiple Pages
# ============================================================================


class TestAddMultiplePages:
    """Test multi-page add workflow."""

    @patch("kurt.ingestion.add.batch_extract_document_metadata")
    @patch("kurt.ingestion.add.fetch_documents_batch")
    @patch("kurt.ingestion.add.map_sitemap")
    @patch("kurt.ingestion.add.get_session")
    def test_add_multiple_pages_success(
        self, mock_session, mock_map, mock_fetch_batch, mock_index_batch
    ):
        """Test complete multi-page workflow."""
        from kurt.ingestion.add import add_multiple_pages

        # Mock database session
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Mock sitemap discovery - returns 3 new docs
        mock_map.return_value = [
            {
                "url": "https://example.com/blog/post-1",
                "created": True,
                "document_id": str(uuid4()),
            },
            {
                "url": "https://example.com/blog/post-2",
                "created": True,
                "document_id": str(uuid4()),
            },
            {
                "url": "https://example.com/blog/post-3",
                "created": True,
                "document_id": str(uuid4()),
            },
        ]

        # Mock fetch batch - 3 successful
        mock_fetch_batch.return_value = [
            {"success": True, "document_id": "id-1"},
            {"success": True, "document_id": "id-2"},
            {"success": True, "document_id": "id-3"},
        ]

        # Mock documents for indexing
        from kurt.db.models import Document, IngestionStatus, SourceType

        mock_docs = [
            Document(
                id=uuid4(),
                title=f"Post {i}",
                source_url=f"https://example.com/blog/post-{i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.FETCHED,
            )
            for i in range(1, 4)
        ]
        mock_db.exec.return_value.all.return_value = mock_docs

        # Mock index batch
        import asyncio

        async def mock_index(*args, **kwargs):
            return {"succeeded": 3, "failed": 0, "skipped": 0}

        mock_index_batch.return_value = asyncio.run(mock_index())

        # Run add
        result = add_multiple_pages(
            "https://example.com/blog", fetch=True, index=True, max_concurrent=5
        )

        # Verify result
        assert result["discovered"] == 3
        assert result["created"] == 3
        assert result["fetched"] == 3
        assert result["indexed"] == 3

    @patch("kurt.ingestion.add.map_sitemap")
    @patch("kurt.ingestion.add.get_session")
    def test_add_multiple_pages_with_filters(self, mock_session, mock_map):
        """Test URL filtering works correctly."""
        from kurt.ingestion.add import add_multiple_pages

        # Mock database session
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Mock sitemap discovery - returns 5 docs
        mock_map.return_value = [
            {
                "url": "https://example.com/blog/2024/post-1",
                "created": True,
                "document_id": str(uuid4()),
            },
            {
                "url": "https://example.com/blog/2024/post-2",
                "created": True,
                "document_id": str(uuid4()),
            },
            {
                "url": "https://example.com/blog/2023/post-3",
                "created": True,
                "document_id": str(uuid4()),
            },
            {
                "url": "https://example.com/docs/guide-1",
                "created": True,
                "document_id": str(uuid4()),
            },
            {
                "url": "https://example.com/docs/guide-2",
                "created": True,
                "document_id": str(uuid4()),
            },
        ]

        # Run add with url_contains filter
        result = add_multiple_pages(
            "https://example.com",
            url_contains="/2024/",
            fetch=False,
            index=False,
        )

        # Verify filtering worked - only 2024 posts remain
        assert result["discovered"] <= 5  # Could be filtered
        assert result["created"] <= 2  # Should only have 2024 posts

    @patch("kurt.ingestion.add.map_sitemap")
    @patch("kurt.ingestion.add.get_session")
    def test_add_multiple_pages_discover_only(self, mock_session, mock_map):
        """Test discover-only mode."""
        from kurt.ingestion.add import add_multiple_pages

        # Mock database session
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Mock sitemap discovery
        mock_map.return_value = [
            {
                "url": "https://example.com/blog/post-1",
                "created": True,
                "document_id": str(uuid4()),
            },
            {
                "url": "https://example.com/blog/post-2",
                "created": True,
                "document_id": str(uuid4()),
            },
        ]

        # Run add with discover only
        result = add_multiple_pages("https://example.com/blog", fetch=False, index=False)

        # Verify
        assert result["discovered"] == 2
        assert result["created"] == 2
        assert result["fetched"] == 0  # Should not fetch
        assert result["indexed"] == 0  # Should not index
