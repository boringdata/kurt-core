"""
Tests for document indexing functionality.

═══════════════════════════════════════════════════════════════════════════════
TEST COVERAGE (9 tests)
═══════════════════════════════════════════════════════════════════════════════

TestExtractDocumentMetadata (5 tests)
────────────────────────────────────────────────────────────────────────────────
  ✓ test_extract_metadata_success
      → Verifies metadata extraction updates Document with indexed metadata

  ✓ test_extract_metadata_skips_unchanged
      → Verifies indexing is skipped when content hash matches

  ✓ test_extract_metadata_not_fetched
      → Verifies error when document is not FETCHED

  ✓ test_extract_metadata_no_content
      → Verifies error when content file is missing

  ✓ test_extract_metadata_empty_content
      → Verifies error when content file is empty

TestBatchExtractDocumentMetadata (2 tests)
────────────────────────────────────────────────────────────────────────────────
  ✓ test_batch_extract_success
      → Verifies batch extraction processes multiple documents in parallel

  ✓ test_batch_extract_with_errors
      → Verifies batch extraction handles errors gracefully

TestSessionIsolation (2 tests - NEW)
────────────────────────────────────────────────────────────────────────────────
  ✓ test_extract_metadata_session_isolation
      → Verifies single document extraction uses same session throughout
      → Tests fix for "already attached to session X (this is Y)" error

  ✓ test_batch_extract_no_session_conflicts
      → Verifies batch extraction handles concurrent processing without conflicts
      → Uses real temp database to test multi-threaded behavior

═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import MagicMock, create_autospec, patch
from uuid import uuid4

import pytest

from kurt.config import KurtConfig
from kurt.db.models import ContentType
from kurt.ingestion.index import (
    DocumentMetadataOutput,
    batch_extract_document_metadata,
    extract_document_metadata,
)


class MockDSpyResult:
    """Mock DSPy result object."""

    def __init__(self, metadata):
        self.metadata = metadata


@pytest.fixture
def mock_document():
    """Create mock document for testing."""
    from kurt.db.models import Document, IngestionStatus, SourceType

    return Document(
        id=uuid4(),
        title="Test Document",
        source_url="https://example.com/test",
        source_type=SourceType.URL,
        content_path="example.com/test.md",
        ingestion_status=IngestionStatus.FETCHED,
    )


@pytest.fixture
def mock_metadata_output():
    """Create mock metadata extraction result."""
    return DocumentMetadataOutput(
        content_type=ContentType.TUTORIAL,
        extracted_title="Machine Learning Guide",
        primary_topics=["Machine Learning", "Python", "Data Science"],
        tools_technologies=["TensorFlow", "Scikit-learn", "Pandas"],
        has_code_examples=True,
        has_step_by_step_procedures=True,
        has_narrative_structure=False,
    )


@patch("kurt.db.database.get_session")
@patch("kurt.document.get_document")
@patch("kurt.config.load_config")
@patch("dspy.ChainOfThought")
@patch("dspy.configure")
@patch("dspy.LM")
@patch("kurt.config.get_config_or_default")
def test_extract_metadata_success(
    mock_config,
    mock_lm,
    mock_configure,
    mock_cot,
    mock_load_config,
    mock_get_doc,
    mock_session,
    mock_document,
    mock_metadata_output,
    tmp_path,
):
    """Test successful metadata extraction."""
    # Setup mocks
    mock_config.return_value.INDEXING_LLM_MODEL = "openai/gpt-4o-mini"
    mock_get_doc.return_value = mock_document

    # Create temporary content file
    content = """
# Machine Learning Guide

This is a tutorial on machine learning using Python.

## Prerequisites
- Python 3.8+
- TensorFlow
- Scikit-learn

## Step 1: Install Dependencies
```python
pip install tensorflow scikit-learn pandas
```

## Step 2: Load Data
Follow these steps to load your dataset...
"""
    content_file = tmp_path / "example.com" / "test.md"
    content_file.parent.mkdir(parents=True)
    content_file.write_text(content)

    # Mock config to return temp directory
    mock_kurt_config = create_autospec(KurtConfig, instance=True)
    mock_kurt_config.get_absolute_sources_path.return_value = tmp_path
    mock_load_config.return_value = mock_kurt_config

    # Mock DSPy extraction
    mock_extractor = MagicMock()
    mock_extractor.return_value = MockDSpyResult(metadata=mock_metadata_output)
    mock_cot.return_value = mock_extractor

    # Mock database session
    mock_db_session = MagicMock()
    mock_session.return_value = mock_db_session

    # Run extraction
    result = extract_document_metadata(str(mock_document.id))

    # Verify results
    assert result["document_id"] == str(mock_document.id)
    assert result["title"] == mock_document.title
    assert result["content_type"] == "tutorial"
    assert len(result["topics"]) == 3
    assert "Machine Learning" in result["topics"]
    assert len(result["tools"]) == 3
    assert "TensorFlow" in result["tools"]
    assert result["skipped"] is False

    # Verify database operations - Document was updated
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Verify Document was updated with indexed_with_hash and indexed_with_git_commit
    updated_doc = mock_db_session.add.call_args[0][0]
    assert updated_doc.indexed_with_hash is not None
    assert updated_doc.content_type == ContentType.TUTORIAL


@patch("kurt.document.get_document")
@patch("kurt.config.load_config")
@patch("kurt.utils.calculate_content_hash")
def test_extract_metadata_skips_unchanged(
    mock_calc_hash, mock_load_config, mock_get_doc, mock_document, tmp_path
):
    """Test that indexing is skipped when content hash matches."""
    # Create content
    content = "Test content"
    content_hash = "abc123hash"

    # Setup document with existing hash
    mock_document.indexed_with_hash = content_hash
    mock_document.content_type = ContentType.TUTORIAL
    mock_document.primary_topics = ["Topic A"]
    mock_document.tools_technologies = ["Tool X"]
    mock_get_doc.return_value = mock_document

    # Create temporary content file
    content_file = tmp_path / "example.com" / "test.md"
    content_file.parent.mkdir(parents=True)
    content_file.write_text(content)

    # Mock config
    mock_kurt_config = create_autospec(KurtConfig, instance=True)
    mock_kurt_config.get_absolute_sources_path.return_value = tmp_path
    mock_load_config.return_value = mock_kurt_config

    # Mock hash calculation to return same hash
    mock_calc_hash.return_value = content_hash

    # Run extraction (without force)
    result = extract_document_metadata(str(mock_document.id), force=False)

    # Verify it was skipped
    assert result["skipped"] is True
    assert result["content_type"] == "tutorial"
    assert result["topics"] == ["Topic A"]
    assert result["tools"] == ["Tool X"]


@patch("kurt.document.get_document")
def test_extract_metadata_not_fetched(mock_get_doc):
    """Test error when document is not FETCHED."""
    from kurt.db.models import Document, IngestionStatus, SourceType

    # Create document with NOT_FETCHED status
    doc = Document(
        id=uuid4(),
        title="Test Document",
        source_url="https://example.com/test",
        source_type=SourceType.URL,
        content_path="example.com/test.md",
        ingestion_status=IngestionStatus.NOT_FETCHED,
    )
    mock_get_doc.return_value = doc

    # Verify error raised
    with pytest.raises(ValueError, match="has not been fetched yet"):
        extract_document_metadata(str(doc.id))


@patch("kurt.document.get_document")
@patch("kurt.config.load_config")
def test_extract_metadata_no_content(mock_load_config, mock_get_doc, mock_document, tmp_path):
    """Test error when content file is missing."""
    mock_get_doc.return_value = mock_document

    # Mock config to return temp directory (but don't create content file)
    mock_kurt_config = create_autospec(KurtConfig, instance=True)
    mock_kurt_config.get_absolute_sources_path.return_value = tmp_path
    mock_load_config.return_value = mock_kurt_config

    # Verify error raised
    with pytest.raises(ValueError, match="Content file not found"):
        extract_document_metadata(str(mock_document.id))


@patch("kurt.document.get_document")
@patch("kurt.config.load_config")
def test_extract_metadata_empty_content(mock_load_config, mock_get_doc, mock_document, tmp_path):
    """Test error when content file is empty."""
    mock_get_doc.return_value = mock_document

    # Create empty content file
    content_file = tmp_path / "example.com" / "test.md"
    content_file.parent.mkdir(parents=True)
    content_file.write_text("")

    # Mock config to return temp directory
    mock_kurt_config = create_autospec(KurtConfig, instance=True)
    mock_kurt_config.get_absolute_sources_path.return_value = tmp_path
    mock_load_config.return_value = mock_kurt_config

    # Verify error raised
    with pytest.raises(ValueError, match="has empty content"):
        extract_document_metadata(str(mock_document.id))


# ============================================================================
# Batch Extraction Tests
# ============================================================================


@pytest.mark.asyncio
@patch("kurt.ingestion.index._extract_document_metadata_worker")
@patch("dspy.ChainOfThought")
@patch("dspy.configure")
@patch("dspy.LM")
@patch("kurt.config.get_config_or_default")
async def test_batch_extract_success(mock_config, mock_lm, mock_configure, mock_cot, mock_worker):
    """Test successful batch metadata extraction."""
    # Setup mocks
    mock_config.return_value.INDEXING_LLM_MODEL = "openai/gpt-4o-mini"

    # Mock worker to return successful results
    doc_id_1 = str(uuid4())
    doc_id_2 = str(uuid4())
    doc_id_3 = str(uuid4())

    def worker_side_effect(doc_id, extractor, force=False):
        return {
            "document_id": doc_id,
            "title": f"Document {doc_id[:8]}",
            "content_type": "tutorial",
            "topics": ["Topic A", "Topic B"],
            "tools": ["Tool X"],
            "skipped": False,
        }

    mock_worker.side_effect = worker_side_effect

    # Run batch extraction
    document_ids = [doc_id_1, doc_id_2, doc_id_3]
    result = await batch_extract_document_metadata(document_ids, max_concurrent=2)

    # Verify results
    assert result["total"] == 3
    assert result["succeeded"] == 3
    assert result["failed"] == 0
    assert len(result["results"]) == 3
    assert len(result["errors"]) == 0

    # Verify all documents were processed
    processed_ids = {r["document_id"] for r in result["results"]}
    assert processed_ids == {doc_id_1, doc_id_2, doc_id_3}

    # Verify DSPy was configured once (in main thread)
    mock_configure.assert_called_once()
    mock_cot.assert_called_once()


@pytest.mark.asyncio
@patch("kurt.ingestion.index._extract_document_metadata_worker")
@patch("dspy.ChainOfThought")
@patch("dspy.configure")
@patch("dspy.LM")
@patch("kurt.config.get_config_or_default")
async def test_batch_extract_with_errors(
    mock_config, mock_lm, mock_configure, mock_cot, mock_worker
):
    """Test batch extraction with some documents failing."""
    # Setup mocks
    mock_config.return_value.INDEXING_LLM_MODEL = "openai/gpt-4o-mini"

    # Mock worker to return mix of success and errors
    doc_id_1 = str(uuid4())
    doc_id_2 = str(uuid4())
    doc_id_3 = str(uuid4())

    def worker_side_effect(doc_id, extractor, force=False):
        if doc_id == doc_id_2:
            raise ValueError("Document not fetched")
        return {
            "document_id": doc_id,
            "title": f"Document {doc_id[:8]}",
            "content_type": "blog",
            "topics": ["Topic A"],
            "tools": [],
            "skipped": False,
        }

    mock_worker.side_effect = worker_side_effect

    # Run batch extraction
    document_ids = [doc_id_1, doc_id_2, doc_id_3]
    result = await batch_extract_document_metadata(document_ids, max_concurrent=2)

    # Verify results
    assert result["total"] == 3
    assert result["succeeded"] == 2
    assert result["failed"] == 1
    assert len(result["results"]) == 2
    assert len(result["errors"]) == 1

    # Verify successful documents
    processed_ids = {r["document_id"] for r in result["results"]}
    assert processed_ids == {doc_id_1, doc_id_3}

    # Verify error document
    assert result["errors"][0]["document_id"] == doc_id_2
    assert "Document not fetched" in result["errors"][0]["error"]


@pytest.mark.asyncio
async def test_extract_metadata_session_isolation(test_db, tmp_path):
    """
    Test that extract_document_metadata uses a single session throughout.

    This test verifies the fix for the session conflict bug where Document objects
    were being attached to one session but then tried to be added to a different session.

    The fix ensures that:
    1. Session is obtained at the start of the function
    2. Document is retrieved using that same session
    3. All operations use the same session throughout
    """
    from kurt.db.models import Document, IngestionStatus, SourceType
    from kurt.ingestion.index import extract_document_metadata

    # Create test document with content
    content_dir = tmp_path / "sources"
    content_dir.mkdir()
    content_file = content_dir / "test.md"
    content_file.write_text("# Test Document\n\nThis is test content for session isolation.")

    doc = Document(
        source_type=SourceType.URL,
        source_url="https://example.com/test",
        title="Test Document",
        ingestion_status=IngestionStatus.FETCHED,
        content_path="test.md",
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    doc_id = str(doc.id)

    # Mock get_session to return our test database session
    with patch("kurt.db.database.get_session", return_value=test_db):
        # Mock config to return test path
        with patch("kurt.config.load_config") as mock_config:
            mock_config_obj = create_autospec(KurtConfig, instance=True)
            mock_config_obj.get_absolute_sources_path.return_value = content_dir
            mock_config.return_value = mock_config_obj

            # Mock DSPy components
            with patch("kurt.config.get_config_or_default") as mock_get_config:
                mock_get_config.return_value.INDEXING_LLM_MODEL = "openai/gpt-4o-mini"

                with patch("dspy.LM"):
                    with patch("dspy.configure"):
                        with patch("dspy.ChainOfThought") as mock_cot:
                            # Mock extractor response - properly structure result.metadata
                            mock_extractor = MagicMock()

                            # Create mock result with metadata attribute
                            mock_result = MagicMock()
                            mock_metadata = MagicMock()
                            mock_metadata.content_type = ContentType.TUTORIAL
                            mock_metadata.primary_topics = ["Testing", "Python"]
                            mock_metadata.tools_technologies = ["pytest"]
                            mock_metadata.has_code_examples = True
                            mock_metadata.has_step_by_step_procedures = True
                            mock_metadata.has_narrative_structure = False
                            mock_metadata.extracted_title = "Test Document"

                            mock_result.metadata = mock_metadata
                            mock_extractor.return_value = mock_result
                            mock_cot.return_value = mock_extractor

                            # Mock git commit hash
                            with patch("kurt.utils.get_git_commit_hash", return_value="abc123"):
                                # This should NOT raise a session conflict error
                                result = extract_document_metadata(doc_id)

                                # Verify extraction succeeded
                                assert result["document_id"] == doc_id
                                assert result["title"] == "Test Document"
                                assert result["content_type"] == "tutorial"
                                assert "Testing" in result["topics"]
                                assert "pytest" in result["tools"]
                                assert result["skipped"] is False

    # Verify document was updated in database
    test_db.refresh(doc)
    assert doc.content_type == ContentType.TUTORIAL
    assert "Testing" in doc.primary_topics
    assert "pytest" in doc.tools_technologies
    assert doc.indexed_with_hash is not None


@pytest.mark.asyncio
async def test_batch_extract_no_session_conflicts(tmp_path):
    """
    Test that batch extraction handles multiple documents without session conflicts.

    This integration test verifies that when processing multiple documents concurrently,
    each worker thread gets its own session and Document object, preventing the
    "already attached to session X (this is Y)" error.

    Uses a real temporary SQLite database to test actual multi-threaded behavior.
    """
    from sqlmodel import Session, SQLModel, create_engine

    from kurt.db.models import Document, IngestionStatus, SourceType
    from kurt.ingestion.index import batch_extract_document_metadata

    # Create a real temporary database file (SQLite doesn't like in-memory DBs across threads)
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    # Create test directory
    content_dir = tmp_path / "sources"
    content_dir.mkdir()

    # Create 5 test documents
    doc_ids = []
    with Session(engine) as session:
        for i in range(5):
            content_file = content_dir / f"test{i}.md"
            content_file.write_text(f"# Test Document {i}\n\nContent for document {i}.")

            doc = Document(
                source_type=SourceType.URL,
                source_url=f"https://example.com/test{i}",
                title=f"Test Document {i}",
                ingestion_status=IngestionStatus.FETCHED,
                content_path=f"test{i}.md",
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            doc_ids.append(str(doc.id))

    # Mock get_session to return NEW sessions from our test engine (each thread gets its own)
    def get_test_session():
        return Session(engine)

    with patch("kurt.db.database.get_session", side_effect=get_test_session):
        # Mock config
        with patch("kurt.config.load_config") as mock_config:
            mock_config_obj = create_autospec(KurtConfig, instance=True)
            mock_config_obj.get_absolute_sources_path.return_value = content_dir
            mock_config.return_value = mock_config_obj

            # Mock DSPy
            with patch("kurt.config.get_config_or_default") as mock_get_config:
                mock_get_config.return_value.INDEXING_LLM_MODEL = "openai/gpt-4o-mini"

                with patch("dspy.LM"):
                    with patch("dspy.configure"):
                        with patch("dspy.ChainOfThought") as mock_cot:
                            # Mock extractor - properly structure result.metadata
                            mock_extractor = MagicMock()

                            # Create mock result with metadata attribute
                            mock_result = MagicMock()
                            mock_metadata = MagicMock()
                            mock_metadata.content_type = ContentType.BLOG
                            mock_metadata.primary_topics = ["Testing"]
                            mock_metadata.tools_technologies = []
                            mock_metadata.has_code_examples = False
                            mock_metadata.has_step_by_step_procedures = False
                            mock_metadata.has_narrative_structure = True
                            mock_metadata.extracted_title = None

                            mock_result.metadata = mock_metadata
                            mock_extractor.return_value = mock_result
                            mock_cot.return_value = mock_extractor

                            with patch("kurt.utils.get_git_commit_hash", return_value="abc123"):
                                # Process all documents concurrently
                                # This should NOT raise session conflict errors
                                result = await batch_extract_document_metadata(
                                    doc_ids,
                                    max_concurrent=3,  # Process 3 at a time
                                    force=False,
                                )

                                # Verify all succeeded
                                assert result["total"] == 5
                                assert result["succeeded"] == 5
                                assert result["failed"] == 0
                                assert len(result["errors"]) == 0

                                # Verify all documents were processed
                                processed_ids = {r["document_id"] for r in result["results"]}
                                assert processed_ids == set(doc_ids)
