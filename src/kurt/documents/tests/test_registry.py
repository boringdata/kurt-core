"""
Tests for DocumentRegistry.
"""

from __future__ import annotations

from kurt.db import managed_session
from kurt.documents import DocumentFilters, DocumentRegistry, DocumentView
from kurt.tools.fetch.models import FetchStatus
from kurt.tools.map.models import MapStatus


class TestDocumentRegistry:
    """Test suite for DocumentRegistry."""

    def test_list_all_documents(self, tmp_project_with_docs):
        """Test listing all documents."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session)

        assert len(docs) == 8
        assert all(isinstance(d, DocumentView) for d in docs)

    def test_list_returns_document_views(self, tmp_project_with_docs):
        """Test that list returns DocumentView objects with correct data."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(ids=["doc-4"]))

        assert len(docs) == 1
        doc = docs[0]
        assert doc.document_id == "doc-4"
        assert doc.source_url == "https://example.com/docs/api"
        assert doc.map_status == MapStatus.SUCCESS
        assert doc.fetch_status == FetchStatus.SUCCESS
        assert doc.content_length == 5000
        assert doc.fetch_engine == "trafilatura"

    def test_get_single_document(self, tmp_project_with_docs):
        """Test getting a single document by ID."""
        registry = DocumentRegistry()

        with managed_session() as session:
            doc = registry.get(session, "doc-1")

        assert doc is not None
        assert doc.document_id == "doc-1"
        assert doc.title == "Introduction"

    def test_get_nonexistent_document(self, tmp_project_with_docs):
        """Test getting a document that doesn't exist."""
        registry = DocumentRegistry()

        with managed_session() as session:
            doc = registry.get(session, "nonexistent")

        assert doc is None

    def test_exists(self, tmp_project_with_docs):
        """Test checking if document exists."""
        registry = DocumentRegistry()

        with managed_session() as session:
            assert registry.exists(session, "doc-1") is True
            assert registry.exists(session, "nonexistent") is False


class TestDocumentFiltering:
    """Test suite for document filtering."""

    def test_filter_by_map_status(self, tmp_project_with_docs):
        """Test filtering by map status."""
        registry = DocumentRegistry()

        with managed_session() as session:
            success = registry.list(session, DocumentFilters(map_status=MapStatus.SUCCESS))
            errors = registry.list(session, DocumentFilters(map_status=MapStatus.ERROR))

        assert len(success) == 7  # All docs except doc-7 (ERROR)
        assert len(errors) == 1  # doc-7

    def test_filter_by_fetch_status(self, tmp_project_with_docs):
        """Test filtering by fetch status."""
        registry = DocumentRegistry()

        with managed_session() as session:
            fetched = registry.list(session, DocumentFilters(fetch_status=FetchStatus.SUCCESS))
            fetch_errors = registry.list(session, DocumentFilters(fetch_status=FetchStatus.ERROR))

        assert len(fetched) == 2  # doc-4, doc-5
        assert len(fetch_errors) == 1  # doc-6

    def test_filter_not_fetched(self, tmp_project_with_docs):
        """Test filtering for documents not yet fetched."""
        registry = DocumentRegistry()

        with managed_session() as session:
            not_fetched = registry.list(session, DocumentFilters(not_fetched=True))

        # doc-1, doc-2, doc-3, doc-7, doc-8 have no fetch record
        assert len(not_fetched) == 5
        doc_ids = {d.document_id for d in not_fetched}
        assert "doc-1" in doc_ids
        assert "doc-2" in doc_ids
        assert "doc-3" in doc_ids
        assert "doc-7" in doc_ids
        assert "doc-8" in doc_ids

    def test_filter_has_error(self, tmp_project_with_docs):
        """Test filtering for documents with errors."""
        registry = DocumentRegistry()

        with managed_session() as session:
            with_errors = registry.list(session, DocumentFilters(has_error=True))

        # doc-6 (fetch error) and doc-7 (map error)
        assert len(with_errors) == 2
        doc_ids = {d.document_id for d in with_errors}
        assert "doc-6" in doc_ids
        assert "doc-7" in doc_ids

    def test_filter_by_discovery_method(self, tmp_project_with_docs):
        """Test filtering by discovery method."""
        registry = DocumentRegistry()

        with managed_session() as session:
            sitemap_docs = registry.list(session, DocumentFilters(discovery_method="sitemap"))
            crawl_docs = registry.list(session, DocumentFilters(discovery_method="crawl"))

        assert len(sitemap_docs) == 4  # doc-1, doc-2, doc-4, doc-5
        assert len(crawl_docs) == 3  # doc-3, doc-6, doc-7

    def test_filter_by_fetch_engine(self, tmp_project_with_docs):
        """Test filtering by fetch engine."""
        registry = DocumentRegistry()

        with managed_session() as session:
            trafilatura_docs = registry.list(session, DocumentFilters(fetch_engine="trafilatura"))
            firecrawl_docs = registry.list(session, DocumentFilters(fetch_engine="firecrawl"))

        assert len(trafilatura_docs) == 1  # doc-4
        assert len(firecrawl_docs) == 1  # doc-5

    def test_filter_with_limit(self, tmp_project_with_docs):
        """Test limit filter."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(limit=3))

        assert len(docs) == 3

    def test_filter_with_offset(self, tmp_project_with_docs):
        """Test offset filter."""
        registry = DocumentRegistry()

        with managed_session() as session:
            all_docs = registry.list(session)
            offset_docs = registry.list(session, DocumentFilters(offset=2))

        assert len(offset_docs) == len(all_docs) - 2

    def test_combined_filters(self, tmp_project_with_docs):
        """Test combining multiple filters."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(
                session,
                DocumentFilters(
                    map_status=MapStatus.SUCCESS,
                    discovery_method="sitemap",
                ),
            )

        # doc-1, doc-2, doc-4, doc-5 are SUCCESS + sitemap
        assert len(docs) == 4


class TestUrlContainsFiltering:
    """Test suite for url_contains filtering with glob support."""

    def test_url_contains_substring(self, tmp_project_with_docs):
        """Test url_contains with simple substring match."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(url_contains="docs"))

        # doc-1, doc-2, doc-4, doc-5, doc-8 have "docs" in URL
        assert len(docs) == 5
        for doc in docs:
            assert "docs" in doc.source_url

    def test_url_contains_glob_pattern(self, tmp_project_with_docs):
        """Test url_contains with glob pattern using *."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(url_contains="*blog*"))

        # doc-3 has "blog" in URL
        assert len(docs) == 1
        assert "blog" in docs[0].source_url

    def test_url_contains_glob_prefix(self, tmp_project_with_docs):
        """Test url_contains with glob pattern at start."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(url_contains="*example.com/docs*"))

        # doc-1, doc-2, doc-4, doc-5 match this pattern
        assert len(docs) == 4

    def test_url_contains_no_match(self, tmp_project_with_docs):
        """Test url_contains with pattern that matches nothing."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(url_contains="nonexistent"))

        assert len(docs) == 0


class TestGlobFiltering:
    """Test suite for glob pattern filtering."""

    def test_include_pattern(self, tmp_project_with_docs):
        """Test include glob pattern."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(include="*/docs/*"))

        # doc-1, doc-2, doc-4, doc-5, doc-8 have /docs/ in URL
        assert len(docs) == 5
        for doc in docs:
            assert "/docs/" in doc.source_url

    def test_exclude_pattern(self, tmp_project_with_docs):
        """Test exclude glob pattern."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(exclude="*/blog/*"))

        # All except doc-3 (blog post)
        assert len(docs) == 7
        for doc in docs:
            assert "/blog/" not in doc.source_url

    def test_include_and_exclude_combined(self, tmp_project_with_docs):
        """Test combining include and exclude patterns."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(
                session, DocumentFilters(include="*example.com*", exclude="*/private/*")
            )

        # All example.com docs except private (doc-6)
        assert len(docs) == 6
        for doc in docs:
            assert "example.com" in doc.source_url
            assert "/private/" not in doc.source_url

    def test_include_with_limit_applies_limit_after_filter(self, tmp_project_with_docs):
        """Test that limit is applied after glob filtering, not before.

        This is critical: if limit is applied at SQL level first, the glob filter
        may receive documents that don't match and return nothing.
        """
        registry = DocumentRegistry()

        with managed_session() as session:
            # There are 4 docs with /docs/ in URL
            # Without the fix, limit=2 at SQL level might return 2 non-docs URLs
            # and glob filter would find nothing
            docs = registry.list(session, DocumentFilters(include="*/docs/*", limit=2))

        # Should return exactly 2 docs matching the pattern
        assert len(docs) == 2
        for doc in docs:
            assert "/docs/" in doc.source_url

    def test_include_with_limit_returns_less_if_fewer_matches(self, tmp_project_with_docs):
        """Test that limit with include returns fewer if not enough matches."""
        registry = DocumentRegistry()

        with managed_session() as session:
            # Only 1 doc matches */blog/*
            docs = registry.list(session, DocumentFilters(include="*/blog/*", limit=10))

        assert len(docs) == 1
        assert "/blog/" in docs[0].source_url

    def test_exclude_with_limit(self, tmp_project_with_docs):
        """Test exclude pattern combined with limit."""
        registry = DocumentRegistry()

        with managed_session() as session:
            # Exclude blog, limit to 3
            docs = registry.list(session, DocumentFilters(exclude="*/blog/*", limit=3))

        assert len(docs) == 3
        for doc in docs:
            assert "/blog/" not in doc.source_url


class TestConvenienceMethods:
    """Test suite for convenience methods."""

    def test_list_fetchable(self, tmp_project_with_docs):
        """Test list_fetchable convenience method."""
        registry = DocumentRegistry()

        with managed_session() as session:
            fetchable = registry.list_fetchable(session)

        # Documents that are mapped but not fetched
        assert len(fetchable) == 5
        for doc in fetchable:
            assert (
                doc.fetch_status in (None, FetchStatus.PENDING, FetchStatus.ERROR)
                or doc.fetch_status is None
            )

    def test_list_with_errors(self, tmp_project_with_docs):
        """Test list_with_errors convenience method."""
        registry = DocumentRegistry()

        with managed_session() as session:
            errors = registry.list_with_errors(session)

        assert len(errors) == 2  # doc-6 and doc-7
        for doc in errors:
            assert doc.has_error is True

    def test_count(self, tmp_project_with_docs):
        """Test count method."""
        registry = DocumentRegistry()

        with managed_session() as session:
            total = registry.count(session)
            success = registry.count(session, DocumentFilters(map_status=MapStatus.SUCCESS))

        assert total == 8
        assert success == 7  # All except doc-7 (ERROR)


class TestDocumentViewProperties:
    """Test suite for DocumentView computed properties."""

    def test_current_stage_mapped(self, tmp_project_with_docs):
        """Test current_stage for mapped-only documents."""
        registry = DocumentRegistry()

        with managed_session() as session:
            doc = registry.get(session, "doc-1")

        assert doc.current_stage == "mapped"

    def test_current_stage_fetched(self, tmp_project_with_docs):
        """Test current_stage for fetched documents."""
        registry = DocumentRegistry()

        with managed_session() as session:
            doc = registry.get(session, "doc-4")

        assert doc.current_stage == "fetched"

    def test_has_error_true(self, tmp_project_with_docs):
        """Test has_error for documents with errors."""
        registry = DocumentRegistry()

        with managed_session() as session:
            map_error = registry.get(session, "doc-7")
            fetch_error = registry.get(session, "doc-6")

        assert map_error.has_error is True
        assert fetch_error.has_error is True

    def test_has_error_false(self, tmp_project_with_docs):
        """Test has_error for healthy documents."""
        registry = DocumentRegistry()

        with managed_session() as session:
            doc = registry.get(session, "doc-4")

        assert doc.has_error is False

    def test_is_fetchable(self, tmp_project_with_docs):
        """Test is_fetchable property."""
        registry = DocumentRegistry()

        with managed_session() as session:
            discovered = registry.get(session, "doc-1")
            already_fetched = registry.get(session, "doc-4")

        assert discovered.is_fetchable is True
        assert already_fetched.is_fetchable is False

    def test_is_fetched(self, tmp_project_with_docs):
        """Test is_fetched property."""
        registry = DocumentRegistry()

        with managed_session() as session:
            fetched = registry.get(session, "doc-4")
            not_fetched = registry.get(session, "doc-1")

        assert fetched.is_fetched is True
        assert not_fetched.is_fetched is False
