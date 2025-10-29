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
from pathlib import Path
from unittest.mock import MagicMock, create_autospec, patch
from uuid import uuid4

import pytest

from kurt.config import KurtConfig
from kurt.ingestion.fetch import (
    _create_content_path,
    _fetch_with_firecrawl,
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
# Firecrawl Fetch Tests
# ============================================================================


class TestFetchWithFirecrawl:
    """Test Firecrawl fetching functionality."""

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test_key_123"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_with_firecrawl_success(self, mock_firecrawl_class):
        """Test successful fetch with Firecrawl using v2 API."""
        # Create mock result object with attributes
        mock_result = MagicMock()
        mock_result.markdown = "# Test Content\n\nThis is test content."
        mock_result.metadata = {"title": "Test Page", "author": "Test Author"}

        # Mock the scrape method
        mock_app = MagicMock()
        mock_app.scrape.return_value = mock_result
        mock_firecrawl_class.return_value = mock_app

        # Test the function
        content, metadata = _fetch_with_firecrawl("https://example.com/test")

        # Verify the scrape method was called correctly (v2 API)
        mock_app.scrape.assert_called_once_with(
            "https://example.com/test", formats=["markdown", "html"]
        )

        # Verify results
        assert content == "# Test Content\n\nThis is test content."
        assert metadata == {"title": "Test Page", "author": "Test Author"}

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test_key_123"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_with_firecrawl_no_markdown(self, mock_firecrawl_class):
        """Test error when Firecrawl returns no markdown."""
        # Create mock result without markdown attribute
        mock_result = MagicMock()
        del mock_result.markdown  # Remove the markdown attribute

        mock_app = MagicMock()
        mock_app.scrape.return_value = mock_result
        mock_firecrawl_class.return_value = mock_app

        # Should raise error
        with pytest.raises(ValueError, match="Firecrawl failed to extract content"):
            _fetch_with_firecrawl("https://example.com/test")

    @patch.dict(os.environ, {}, clear=True)
    def test_fetch_with_firecrawl_no_api_key(self):
        """Test error when API key is not set."""
        with pytest.raises(ValueError, match="FIRECRAWL_API_KEY not set"):
            _fetch_with_firecrawl("https://example.com/test")

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test_key_123"})
    @patch("firecrawl.FirecrawlApp")
    def test_fetch_with_firecrawl_empty_metadata(self, mock_firecrawl_class):
        """Test fetch with empty metadata."""
        # Create mock result with no metadata
        mock_result = MagicMock()
        mock_result.markdown = "# Test Content"
        mock_result.metadata = None

        mock_app = MagicMock()
        mock_app.scrape.return_value = mock_result
        mock_firecrawl_class.return_value = mock_app

        content, metadata = _fetch_with_firecrawl("https://example.com/test")

        assert content == "# Test Content"
        assert metadata == {}


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
# Fetch Document UUID Handling Tests
# ============================================================================


class TestFetchDocumentUUIDHandling:
    """Test that fetch_document handles both UUID objects and strings."""

    @patch("kurt.ingestion.fetch.get_session")
    @patch("kurt.ingestion.fetch._get_fetch_engine")
    @patch("kurt.ingestion.fetch._fetch_with_trafilatura")
    @patch("kurt.ingestion.fetch.load_config")
    def test_fetch_document_with_uuid_object(
        self, mock_config, mock_trafilatura, mock_engine, mock_session
    ):
        """Test that fetch_document accepts UUID objects (not just strings)."""

        from kurt.db.models import Document, IngestionStatus, SourceType

        # Create a test UUID
        test_uuid = uuid4()

        # Mock the database session
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Create mock document
        mock_doc = Document(
            id=test_uuid,
            title="Test Document",
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        mock_db.get.return_value = mock_doc

        # Mock fetch engine and trafilatura
        mock_engine.return_value = "trafilatura"
        mock_trafilatura.return_value = ("# Test Content", {"title": "Test"})

        # Mock config
        mock_config_obj = MagicMock()
        mock_config_obj.get_absolute_sources_path.return_value = Path("/tmp/sources")
        mock_config.return_value = mock_config_obj

        # This should NOT raise an AttributeError about 'replace'
        # (which was the bug: UUID(uuid_object) tried to call uuid_object.replace())
        from kurt.ingestion.fetch import fetch_document

        try:
            result = fetch_document(test_uuid)  # Pass UUID object, not string
            # If we get here, the bug is fixed
            assert result is not None
        except AttributeError as e:
            if "replace" in str(e):
                pytest.fail(
                    "fetch_document should accept UUID objects, but got AttributeError about 'replace'"
                )
            raise

    @patch("kurt.ingestion.fetch.get_session")
    @patch("kurt.ingestion.fetch._get_fetch_engine")
    @patch("kurt.ingestion.fetch._fetch_with_trafilatura")
    @patch("kurt.ingestion.fetch.load_config")
    def test_fetch_document_with_uuid_string(
        self, mock_config, mock_trafilatura, mock_engine, mock_session
    ):
        """Test that fetch_document still accepts UUID strings."""
        from kurt.db.models import Document, IngestionStatus, SourceType

        # Create a test UUID string
        test_uuid = uuid4()
        test_uuid_str = str(test_uuid)

        # Mock the database session
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Create mock document
        mock_doc = Document(
            id=test_uuid,
            title="Test Document",
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        mock_db.get.return_value = mock_doc

        # Mock fetch engine and trafilatura
        mock_engine.return_value = "trafilatura"
        mock_trafilatura.return_value = ("# Test Content", {"title": "Test"})

        # Mock config
        mock_config_obj = MagicMock()
        mock_config_obj.get_absolute_sources_path.return_value = Path("/tmp/sources")
        mock_config.return_value = mock_config_obj

        from kurt.ingestion.fetch import fetch_document

        result = fetch_document(test_uuid_str)  # Pass UUID as string
        assert result is not None


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
