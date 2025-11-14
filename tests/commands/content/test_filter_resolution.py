"""Tests for filter resolution utility."""

from uuid import uuid4

import pytest

from kurt.content.filtering import DocumentFilters, resolve_filters
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType


class TestFilterResolution:
    """Test the filter resolution utility function."""

    def test_resolve_filters_no_args(self):
        """Test with no arguments returns empty filters."""
        filters = resolve_filters()
        assert filters.ids is None
        assert filters.include_pattern is None
        assert filters.in_cluster is None
        assert filters.with_status is None
        assert filters.with_content_type is None
        assert filters.limit is None
        assert filters.exclude_pattern is None

    def test_resolve_filters_passes_through_basic_filters(self):
        """Test that basic filters are passed through unchanged."""
        filters = resolve_filters(
            include_pattern="*/docs/*",
            in_cluster="Tutorials",
            with_status="FETCHED",
            with_content_type="tutorial",
            limit=10,
            exclude_pattern="*/ignore/*",
        )
        assert filters.include_pattern == "*/docs/*"
        assert filters.in_cluster == "Tutorials"
        assert filters.with_status == "FETCHED"
        assert filters.with_content_type == "tutorial"
        assert filters.limit == 10
        assert filters.exclude_pattern == "*/ignore/*"

    def test_resolve_filters_identifier_only(self, isolated_cli_runner):
        """Test with identifier only resolves to full UUID."""
        runner, project_dir = isolated_cli_runner
        session = get_session()

        # Create a document
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name="Test Document",
            source_url="https://example.com/doc",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(doc)
        session.commit()

        # Test with full UUID
        filters = resolve_filters(identifier=str(doc_id))
        assert filters.ids == str(doc_id)

        # Test with partial UUID
        partial = str(doc_id)[:8]
        filters = resolve_filters(identifier=partial)
        assert filters.ids == str(doc_id)

    def test_resolve_filters_identifier_with_url(self, isolated_cli_runner):
        """Test identifier resolution with URL."""
        runner, project_dir = isolated_cli_runner
        session = get_session()

        # Create document with URL
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name="Test Document",
            source_url="https://example.com/article",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(doc)
        session.commit()

        # Resolve by URL
        filters = resolve_filters(identifier="https://example.com/article")
        assert filters.ids == str(doc_id)

    def test_resolve_filters_identifier_with_file_path(self, isolated_cli_runner):
        """Test identifier resolution with file path."""
        runner, project_dir = isolated_cli_runner
        session = get_session()

        # Create document with file path
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name="Test Document",
            content_path="example.com/article.md",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(doc)
        session.commit()

        # Resolve by file path
        filters = resolve_filters(identifier="example.com/article.md")
        assert filters.ids == str(doc_id)

    def test_resolve_filters_merges_identifier_and_ids(self, isolated_cli_runner):
        """Test that identifier is merged into ids parameter."""
        runner, project_dir = isolated_cli_runner
        session = get_session()

        # Create documents
        doc1_id = uuid4()
        doc1 = Document(
            id=doc1_id,
            name="Doc 1",
            source_url="https://example.com/doc1",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc2_id = uuid4()
        doc2 = Document(
            id=doc2_id,
            name="Doc 2",
            source_url="https://example.com/doc2",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add_all([doc1, doc2])
        session.commit()

        # Resolve with both identifier and ids
        partial1 = str(doc1_id)[:8]
        filters = resolve_filters(identifier=partial1, ids=str(doc2_id))

        # Should merge: identifier comes first
        assert filters.ids == f"{doc1_id},{doc2_id}"

    def test_resolve_filters_invalid_identifier_raises(self, isolated_cli_runner):
        """Test that invalid identifier raises ValueError."""
        runner, project_dir = isolated_cli_runner

        with pytest.raises(ValueError, match="Failed to resolve identifier"):
            resolve_filters(identifier="nonexistent")

    def test_resolve_filters_combines_all(self, isolated_cli_runner):
        """Test combining identifier with all other filters."""
        runner, project_dir = isolated_cli_runner
        session = get_session()

        # Create document
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            name="Test Document",
            source_url="https://example.com/doc",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(doc)
        session.commit()

        # Resolve with all parameters
        partial = str(doc_id)[:8]
        filters = resolve_filters(
            identifier=partial,
            ids="other-id",
            include_pattern="*/docs/*",
            in_cluster="Tutorials",
            with_status="FETCHED",
            with_content_type="tutorial",
            limit=5,
            exclude_pattern="*/ignore/*",
        )

        # Check all filters are set correctly
        assert f"{doc_id},other-id" == filters.ids
        assert filters.include_pattern == "*/docs/*"
        assert filters.in_cluster == "Tutorials"
        assert filters.with_status == "FETCHED"
        assert filters.with_content_type == "tutorial"
        assert filters.limit == 5
        assert filters.exclude_pattern == "*/ignore/*"


class TestDocumentFiltersDataclass:
    """Test the DocumentFilters dataclass."""

    def test_document_filters_defaults(self):
        """Test that all fields default to None."""
        filters = DocumentFilters()
        assert filters.ids is None
        assert filters.include_pattern is None
        assert filters.in_cluster is None
        assert filters.with_status is None
        assert filters.with_content_type is None
        assert filters.limit is None
        assert filters.exclude_pattern is None

    def test_document_filters_initialization(self):
        """Test initializing with values."""
        filters = DocumentFilters(
            ids="id1,id2",
            include_pattern="*/docs/*",
            in_cluster="Tutorials",
            with_status="FETCHED",
            with_content_type="tutorial",
            limit=10,
            exclude_pattern="*/ignore/*",
        )
        assert filters.ids == "id1,id2"
        assert filters.include_pattern == "*/docs/*"
        assert filters.in_cluster == "Tutorials"
        assert filters.with_status == "FETCHED"
        assert filters.with_content_type == "tutorial"
        assert filters.limit == 10
        assert filters.exclude_pattern == "*/ignore/*"

    def test_document_filters_partial_initialization(self):
        """Test initializing with only some values."""
        filters = DocumentFilters(ids="id1", limit=5)
        assert filters.ids == "id1"
        assert filters.limit == 5
        assert filters.include_pattern is None
        assert filters.in_cluster is None
