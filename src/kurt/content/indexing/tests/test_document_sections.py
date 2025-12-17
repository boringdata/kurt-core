"""
Comprehensive unit tests for the document_sections model.

Tests section splitting, skip behavior, section hashing, and edge cases.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pandas as pd
import pytest
from sqlmodel import create_engine

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing.step_document_sections import (
    DocumentSectionRow,
    DocumentSectionsConfig,
    document_sections,
)
from kurt.core import PipelineContext, TableWriter


class TestDocumentSectionsModel:
    """Test suite for the document_sections model."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            engine = create_engine(f"sqlite:///{db_path}")
            DocumentSectionRow.metadata.create_all(engine)
            yield db_path

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_document_sections"}
        return writer

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    def _create_mock_reference(self, documents: list[dict]):
        """Create a mock Reference that returns the documents DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(documents)
        return mock_ref

    def test_single_small_section(self, mock_writer, mock_ctx):
        """Test document that fits in a single section."""
        doc_id = str(uuid4())
        content = "This is a short document that fits in a single section."

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": content,
                    "skip": False,
                    "error": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_document_sections",
        }

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        assert result["rows_written"] == 1
        mock_writer.write.assert_called_once()
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].document_id == doc_id

    def test_multiple_sections_with_overlap(self, mock_writer, mock_ctx):
        """Test document split into multiple sections with overlap."""
        doc_id = str(uuid4())
        # Create content that will span multiple sections (default max is 5000 chars)
        max_chars = 5000
        content = "# Section One\n\n" + "A" * (max_chars - 100)
        content += "\n\n# Section Two\n\n" + "B" * (max_chars - 100)
        content += "\n\n# Section Three\n\n" + "C" * 500

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": content,
                    "skip": False,
                    "error": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 3,
            "table_name": "indexing_document_sections",
        }

        document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Should create multiple sections
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) >= 2

        # Verify sections have proper structure
        for row in rows:
            assert row.document_id == doc_id
            assert row.section_number >= 1
            assert row.content
            assert row.section_hash  # Hash should be computed

    def test_skip_behavior(self, mock_writer, mock_ctx):
        """Test that documents marked as skip are not processed."""
        doc_id = str(uuid4())

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": "Content that should be skipped",
                    "skip": True,
                    "error": None,
                }
            ]
        )

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Should not write any rows
        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    def test_error_document_skipped(self, mock_writer, mock_ctx):
        """Test that documents with errors are skipped."""
        doc_id = str(uuid4())

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": "",
                    "skip": False,
                    "error": "Failed to load content",
                }
            ]
        )

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Should not write any rows
        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    def test_section_hash_consistency(self, mock_writer, mock_ctx):
        """Test that section hashes are consistent and deterministic."""
        doc_id = str(uuid4())
        content = "Test content for hash consistency"

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": content,
                    "skip": False,
                    "error": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_document_sections",
        }

        # Run first time
        document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)
        rows1 = mock_writer.write.call_args[0][0]
        hash1 = rows1[0].section_hash

        # Run second time with same content
        mock_writer.reset_mock()
        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": content,
                    "skip": False,
                    "error": None,
                }
            ]
        )
        document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)
        rows2 = mock_writer.write.call_args[0][0]
        hash2 = rows2[0].section_hash

        # Hashes should be the same for same content
        assert hash1 == hash2

    def test_empty_content_handling(self, mock_writer, mock_ctx):
        """Test handling of documents with no content."""
        doc_id = str(uuid4())

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": "",  # Empty content
                    "skip": False,
                    "error": None,
                }
            ]
        )

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Should not write any sections for empty content
        assert result["rows_written"] == 0

    def test_markdown_heading_preservation(self, mock_writer, mock_ctx):
        """Test that markdown headings are preserved in sections."""
        doc_id = str(uuid4())
        content = """# Main Title

## Subsection One
Content for subsection one.

## Subsection Two
Content for subsection two.

### Sub-subsection
Nested content here.
"""

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": content,
                    "skip": False,
                    "error": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_document_sections",
        }

        document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        rows = mock_writer.write.call_args[0][0]
        assert len(rows) >= 1

        # The content should be preserved
        assert "Main Title" in rows[0].content or rows[0].heading is not None

    def test_section_ordering(self, mock_writer, mock_ctx):
        """Test that sections maintain correct ordering."""
        doc_id = str(uuid4())
        # Create content with numbered sections for easy verification
        content = "\n\n".join([f"# Section {i}\n" + f"Content {i}" * 100 for i in range(1, 11)])

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": content,
                    "skip": False,
                    "error": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 5,
            "table_name": "indexing_document_sections",
        }

        document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        rows = mock_writer.write.call_args[0][0]

        # Verify section numbers are sequential
        section_numbers = [r.section_number for r in rows]
        assert section_numbers == sorted(section_numbers)
        assert section_numbers[0] == 1

        # Verify offsets are sequential
        prev_end = 0
        for row in sorted(rows, key=lambda r: r.section_number):
            assert row.start_offset >= prev_end
            prev_end = row.end_offset

    def test_batch_processing(self, mock_writer, mock_ctx):
        """Test processing multiple documents in a single batch."""
        documents = []
        doc_ids = []

        for i in range(5):
            doc_id = str(uuid4())
            doc_ids.append(doc_id)
            documents.append(
                {
                    "document_id": doc_id,
                    "title": f"Doc {i}",
                    "content": f"Document {i} content\n" * 100,
                    "skip": False,
                    "error": None,
                }
            )

        mock_documents = self._create_mock_reference(documents)

        mock_writer.write.return_value = {
            "rows_written": 5,
            "table_name": "indexing_document_sections",
        }

        document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Should have written sections for all documents
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) >= len(documents)

        # Verify each document has sections
        doc_ids_in_rows = {r.document_id for r in rows}
        for doc_id in doc_ids:
            assert doc_id in doc_ids_in_rows

    def test_document_title_preserved(self, mock_writer, mock_ctx):
        """Test that document title is preserved in sections."""
        doc_id = str(uuid4())

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "My Important Document",
                    "content": "Test content for title verification",
                    "skip": False,
                    "error": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_document_sections",
        }

        document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        rows = mock_writer.write.call_args[0][0]
        assert rows[0].document_title == "My Important Document"

    def test_empty_dataframe(self, mock_writer, mock_ctx):
        """Test handling of empty documents DataFrame."""
        mock_documents = self._create_mock_reference([])

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    def test_mixed_skip_and_process(self, mock_writer, mock_ctx):
        """Test batch with some documents skipped and some processed."""
        process_doc_id = str(uuid4())
        documents = [
            {
                "document_id": str(uuid4()),
                "title": "Skip Doc",
                "content": "Skip content",
                "skip": True,
                "error": None,
            },
            {
                "document_id": process_doc_id,
                "title": "Process Doc",
                "content": "Process content",
                "skip": False,
                "error": None,
            },
            {
                "document_id": str(uuid4()),
                "title": "Error Doc",
                "content": "",
                "skip": False,
                "error": "Content load failed",
            },
        ]

        mock_documents = self._create_mock_reference(documents)

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_document_sections",
        }

        document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Only one document should be processed
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].document_id == process_doc_id

    def test_config_values_used(self, mock_writer, mock_ctx):
        """Test that config values are applied to splitting."""
        doc_id = str(uuid4())
        # Create content with paragraphs that will be split (splitter uses \n\n as break points)
        # Each paragraph is ~300 chars, total ~1200 chars
        para1 = "A" * 300
        para2 = "B" * 300
        para3 = "C" * 300
        para4 = "D" * 300
        content = f"{para1}\n\n{para2}\n\n{para3}\n\n{para4}"

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": content,
                    "skip": False,
                    "error": None,
                }
            ]
        )

        # Create custom config - max 500 chars per section
        config = DocumentSectionsConfig(
            max_section_chars=500,
            overlap_chars=50,
            min_section_size=100,
        )

        mock_writer.write.return_value = {
            "rows_written": 3,
            "table_name": "indexing_document_sections",
        }

        document_sections(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=config,
        )

        # With max 500 chars and ~1200 char content (4 paragraphs of 300 chars each),
        # should split into multiple sections (2-3 sections expected)
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) >= 2

    def test_skip_reason_content_unchanged(self, mock_writer, mock_ctx):
        """Test that skip_reason='content_unchanged' is respected."""
        doc_id = str(uuid4())

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Unchanged Doc",
                    "content": "This content has not changed",
                    "skip": True,
                    "skip_reason": "content_unchanged",
                    "error": None,
                    "indexed_with_hash": "abc123",
                    "content_hash": "abc123",
                }
            ]
        )

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Should not write any rows - document was skipped
        assert result["rows_written"] == 0
        assert result.get("skipped", 0) == 1
        mock_writer.write.assert_not_called()

    def test_reprocess_unchanged_context_flag(self):
        """Test that PipelineContext properly passes reprocess_unchanged."""
        # Test with reprocess_unchanged=False (default)
        ctx_default = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test",
        )
        assert ctx_default.reprocess_unchanged is False

        # Test with reprocess_unchanged=True
        ctx_force = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test",
            reprocess_unchanged=True,
        )
        assert ctx_force.reprocess_unchanged is True

    def test_skip_with_indexed_with_hash_metadata(self, mock_writer, mock_ctx):
        """Test that indexed_with_hash metadata flows through correctly."""
        doc_id = str(uuid4())
        content_hash = "sha256_hash_value"

        # Document that was previously indexed (has indexed_with_hash)
        # but content has changed (different content_hash)
        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Changed Doc",
                    "content": "New content that should be processed",
                    "skip": False,
                    "skip_reason": None,
                    "error": None,
                    "indexed_with_hash": "old_hash",  # Previous indexing hash
                    "content_hash": content_hash,  # Current content hash (different)
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_document_sections",
        }

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Should process - content changed
        assert result["documents"] == 1
        assert result.get("skipped", 0) == 0
        mock_writer.write.assert_called_once()
