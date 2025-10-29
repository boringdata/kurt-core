"""
Tests for document fetching functionality.

═══════════════════════════════════════════════════════════════════════════════
TEST COVERAGE
═══════════════════════════════════════════════════════════════════════════════

TestGetFetchEngine
────────────────────────────────────────────────────────────────────────────────
  ✓ test_get_fetch_engine_default_trafilatura
      → Verifies Trafilatura is default when no API key

  ✓ test_get_fetch_engine_override_trafilatura
      → Verifies override to Trafilatura works

  ✓ test_get_fetch_engine_override_firecrawl_no_key
      → Verifies error when Firecrawl requested without API key

TestCreateContentPath
────────────────────────────────────────────────────────────────────────────────
  ✓ test_create_content_path
      → Verifies URL is converted to valid file path

TestAddDocument
────────────────────────────────────────────────────────────────────────────────
  ✓ test_add_document_new
      → Verifies new document creation

  ✓ test_add_document_existing
      → Verifies returning existing document ID

═══════════════════════════════════════════════════════════════════════════════
"""

import os
from unittest.mock import MagicMock, create_autospec, patch
from uuid import uuid4

import pytest

from kurt.config import KurtConfig
from kurt.ingestion.fetch import (
    _create_content_path,
    _get_fetch_engine,
    add_document,
)

# ============================================================================
# Fetch Engine Selection Tests
# ============================================================================


class TestGetFetchEngine:
    """Test fetch engine selection logic."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("kurt.ingestion.fetch.load_config")
    def test_get_fetch_engine_default_trafilatura(self, mock_load_config):
        """Test default to Trafilatura when no API key."""
        # Mock config with trafilatura default
        mock_config = create_autospec(KurtConfig, instance=True)
        mock_config.INGESTION_FETCH_ENGINE = "trafilatura"
        mock_load_config.return_value = mock_config

        engine = _get_fetch_engine()
        assert engine == "trafilatura"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_fetch_engine_override_trafilatura(self):
        """Test override to Trafilatura."""
        engine = _get_fetch_engine(override="trafilatura")
        assert engine == "trafilatura"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_fetch_engine_override_firecrawl_no_key(self):
        """Test error when Firecrawl requested without API key."""
        with pytest.raises(ValueError, match="FIRECRAWL_API_KEY not set"):
            _get_fetch_engine(override="firecrawl")

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test_key_123"})
    def test_get_fetch_engine_override_firecrawl_with_key(self):
        """Test Firecrawl override with valid API key."""
        engine = _get_fetch_engine(override="firecrawl")
        assert engine == "firecrawl"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_fetch_engine_invalid_override(self):
        """Test error on invalid engine override."""
        with pytest.raises(ValueError, match="Invalid fetch engine"):
            _get_fetch_engine(override="invalid_engine")


# ============================================================================
# Content Path Tests
# ============================================================================


class TestCreateContentPath:
    """Test content path generation."""

    def test_create_content_path(self, tmp_path):
        """Test URL is converted to valid file path."""
        # Mock config
        mock_config = create_autospec(KurtConfig, instance=True)
        mock_config.get_absolute_sources_path.return_value = tmp_path

        path = _create_content_path("https://example.com/blog/my-post", mock_config)

        # Verify path structure
        assert path.suffix == ".md"
        assert "blog" in str(path)
        # Path should be under sources_path/example.com/...
        assert "example.com" in str(path)

    def test_create_content_path_with_query_params(self, tmp_path):
        """Test URL with query parameters."""
        mock_config = create_autospec(KurtConfig, instance=True)
        mock_config.get_absolute_sources_path.return_value = tmp_path

        path = _create_content_path("https://example.com/page?id=123", mock_config)

        # Verify query params are handled
        assert path.suffix == ".md"
        assert path.parent.name == "example.com"


# ============================================================================
# Add Document Tests
# ============================================================================


class TestAddDocument:
    """Test document addition to database."""

    @patch("kurt.ingestion.fetch.get_session")
    def test_add_document_new(self, mock_session):
        """Test creating a new document."""
        # Mock database session - no existing document
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.exec.return_value.first.return_value = None

        # Create document
        doc_id = add_document("https://example.com/test", title="Test Page")

        # Verify document was added
        assert doc_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("kurt.ingestion.fetch.get_session")
    def test_add_document_existing(self, mock_session):
        """Test returning existing document ID."""
        from kurt.db.models import Document, IngestionStatus, SourceType

        # Mock database session - existing document
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        existing_doc = Document(
            id=uuid4(),
            title="Existing Doc",
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        mock_db.exec.return_value.first.return_value = existing_doc

        # Add document
        doc_id = add_document("https://example.com/test")

        # Verify existing document ID returned
        assert str(doc_id) == str(existing_doc.id)
        mock_db.add.assert_not_called()  # Should not create new


# ============================================================================
# Fetch Document Tests (with test database)
# ============================================================================


class TestFetchDocumentWithDB:
    """Test document fetching workflow with isolated test database."""

    def test_add_document_with_db(self, test_db):
        """Test add_document creates document in database."""
        # Add a document
        with patch("kurt.ingestion.fetch.get_session", return_value=test_db):
            doc_id = add_document("https://example.com/test", title="Test Doc")

        # Verify it was created
        from sqlmodel import select

        from kurt.db.models import Document

        stmt = select(Document).where(Document.id == doc_id)
        doc = test_db.exec(stmt).first()

        assert doc is not None
        assert doc.source_url == "https://example.com/test"
        assert doc.title == "Test Doc"

    def test_add_document_duplicate(self, test_db):
        """Test add_document returns existing document ID for duplicates."""
        from kurt.db.models import Document, IngestionStatus, SourceType

        # Create initial document
        doc = Document(
            title="Existing",
            source_url="https://example.com/duplicate",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        test_db.add(doc)
        test_db.commit()
        test_db.refresh(doc)
        original_id = doc.id

        # Try to add same URL
        with patch("kurt.ingestion.fetch.get_session", return_value=test_db):
            returned_id = add_document("https://example.com/duplicate")

        # Should return existing document ID
        assert str(returned_id) == str(original_id)
