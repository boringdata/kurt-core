"""
Tests for document indexing functionality.

═══════════════════════════════════════════════════════════════════════════════
TEST COVERAGE (7 tests)
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

═══════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from kurt.indexing import (
    DocumentMetadataOutput,
    batch_extract_document_metadata,
    extract_document_metadata,
)
from kurt.models.models import ContentType


class MockDSpyResult:
    """Mock DSPy result object."""

    def __init__(self, metadata):
        self.metadata = metadata


@pytest.fixture
def mock_document():
    """Create mock document for testing."""
    from kurt.models.models import Document, IngestionStatus, SourceType

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


@patch("kurt.database.get_session")
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
    mock_config.return_value.LLM_MODEL_DOC_PROCESSING = "openai/gpt-4o-mini"
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
    mock_kurt_config = MagicMock()
    mock_kurt_config.get_absolute_source_path.return_value = tmp_path
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
    mock_kurt_config = MagicMock()
    mock_kurt_config.get_absolute_source_path.return_value = tmp_path
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
    from kurt.models.models import Document, IngestionStatus, SourceType

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
    mock_kurt_config = MagicMock()
    mock_kurt_config.get_absolute_source_path.return_value = tmp_path
    mock_load_config.return_value = mock_kurt_config

    # Verify error raised
    with pytest.raises(ValueError, match="Content file not found"):
        extract_document_metadata(str(mock_document.id))


@patch("kurt.document.get_document")
@patch("kurt.config.load_config")
def test_extract_metadata_empty_content(
    mock_load_config, mock_get_doc, mock_document, tmp_path
):
    """Test error when content file is empty."""
    mock_get_doc.return_value = mock_document

    # Create empty content file
    content_file = tmp_path / "example.com" / "test.md"
    content_file.parent.mkdir(parents=True)
    content_file.write_text("")

    # Mock config to return temp directory
    mock_kurt_config = MagicMock()
    mock_kurt_config.get_absolute_source_path.return_value = tmp_path
    mock_load_config.return_value = mock_kurt_config

    # Verify error raised
    with pytest.raises(ValueError, match="has empty content"):
        extract_document_metadata(str(mock_document.id))


# ============================================================================
# Batch Extraction Tests
# ============================================================================


@pytest.mark.asyncio
@patch("kurt.indexing._extract_document_metadata_worker")
@patch("dspy.ChainOfThought")
@patch("dspy.configure")
@patch("dspy.LM")
@patch("kurt.config.get_config_or_default")
async def test_batch_extract_success(
    mock_config, mock_lm, mock_configure, mock_cot, mock_worker
):
    """Test successful batch metadata extraction."""
    # Setup mocks
    mock_config.return_value.LLM_MODEL_DOC_PROCESSING = "openai/gpt-4o-mini"

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
@patch("kurt.indexing._extract_document_metadata_worker")
@patch("dspy.ChainOfThought")
@patch("dspy.configure")
@patch("dspy.LM")
@patch("kurt.config.get_config_or_default")
async def test_batch_extract_with_errors(
    mock_config, mock_lm, mock_configure, mock_cot, mock_worker
):
    """Test batch extraction with some documents failing."""
    # Setup mocks
    mock_config.return_value.LLM_MODEL_DOC_PROCESSING = "openai/gpt-4o-mini"

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
