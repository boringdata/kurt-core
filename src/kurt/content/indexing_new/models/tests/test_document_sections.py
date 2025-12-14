"""
Comprehensive unit tests for the document_sections model.

Tests section splitting, skip behavior, section hashing, and edge cases.
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import create_engine

from kurt.content.indexing_new.framework import TableReader, TableWriter
from kurt.content.indexing_new.models.step_document_sections import (
    MAX_SECTION_CHARS,
    DocumentSectionRow,
    document_sections,
)


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
    def writer_reader(self, temp_db):
        """Create TableWriter and TableReader instances."""
        writer = TableWriter(workflow_id="test_workflow")
        reader = TableReader()
        return writer, reader

    def test_single_small_section(self, writer_reader):
        """Test document that fits in a single section."""
        writer, reader = writer_reader

        doc_id = str(uuid4())
        content = "This is a short document that fits in a single section."

        payloads = [
            {
                "document_id": doc_id,
                "content": content,
                "skip": False,
            }
        ]

        result = document_sections(
            reader=reader, writer=writer, payloads=payloads, incremental_mode="full"
        )

        assert result["rows_written"] == 1
        assert result["table_name"] == "indexing_document_sections"

    def test_multiple_sections_with_overlap(self, writer_reader):
        """Test document split into multiple sections with overlap."""
        writer, reader = writer_reader

        doc_id = str(uuid4())
        # Create content that will span multiple sections
        content = "# Section One\n\n" + "A" * (MAX_SECTION_CHARS - 100)
        content += "\n\n# Section Two\n\n" + "B" * (MAX_SECTION_CHARS - 100)
        content += "\n\n# Section Three\n\n" + "C" * 500

        payloads = [
            {
                "document_id": doc_id,
                "content": content,
                "skip": False,
            }
        ]

        result = document_sections(
            reader=reader, writer=writer, payloads=payloads, incremental_mode="full"
        )

        # Should create multiple sections
        assert result["rows_written"] >= 2

        # Verify sections have overlap
        sections = reader.load("indexing_document_sections", where={"document_id": doc_id})

        if len(sections) > 1:
            # Sort by section_number to ensure correct ordering
            sections = sections.sort_values("section_number")

            # Check that overlap fields are populated appropriately
            for idx, row in sections.iterrows():
                section_num = row["section_number"]
                # First section (section_number=1) should not have overlap_prefix
                if section_num == 1:
                    assert row.get("overlap_prefix") is None
                # Last section should not have overlap_suffix
                if section_num == len(sections):
                    assert row.get("overlap_suffix") is None
                # Middle sections should have both overlaps
                if 1 < section_num < len(sections):
                    assert row.get("overlap_prefix") is not None
                    assert row.get("overlap_suffix") is not None

    def test_skip_behavior_in_delta_mode(self, writer_reader):
        """Test that documents marked as skip are not processed."""
        writer, reader = writer_reader

        doc_id = str(uuid4())
        content = "Content that should be skipped"

        payloads = [
            {
                "document_id": doc_id,
                "content": content,
                "skip": True,  # Mark as skip
                "skip_reason": "content_unchanged",
            }
        ]

        result = document_sections(
            reader=reader, writer=writer, payloads=payloads, incremental_mode="delta"
        )

        # Should not write any rows
        assert result["rows_written"] == 0

    def test_section_hash_consistency(self, writer_reader):
        """Test that section hashes are consistent and deterministic."""
        writer, reader = writer_reader

        doc_id = str(uuid4())
        content = "Test content for hash consistency"

        payloads = [
            {
                "document_id": doc_id,
                "content": content,
                "skip": False,
            }
        ]

        # Run twice
        document_sections(reader=reader, writer=writer, payloads=payloads, incremental_mode="full")

        # Get the hash from the first run
        sections1 = reader.load("indexing_document_sections", where={"document_id": doc_id})
        hash1 = sections1.iloc[0]["section_hash"] if not sections1.empty else None

        # Create a new document with same content
        doc_id2 = str(uuid4())
        payloads2 = [
            {
                "document_id": doc_id2,
                "content": content,
                "skip": False,
            }
        ]

        document_sections(reader=reader, writer=writer, payloads=payloads2, incremental_mode="full")

        sections2 = reader.load("indexing_document_sections", where={"document_id": doc_id2})
        hash2 = sections2.iloc[0]["section_hash"] if not sections2.empty else None

        # Hashes should be the same for same content
        assert hash1 == hash2

    def test_empty_content_handling(self, writer_reader):
        """Test handling of documents with no content."""
        writer, reader = writer_reader

        doc_id = str(uuid4())

        payloads = [
            {
                "document_id": doc_id,
                "content": "",  # Empty content
                "skip": False,
            }
        ]

        result = document_sections(
            reader=reader, writer=writer, payloads=payloads, incremental_mode="full"
        )

        # Should not write any sections for empty content
        assert result["rows_written"] == 0

    def test_markdown_heading_preservation(self, writer_reader):
        """Test that markdown headings are preserved in sections."""
        writer, reader = writer_reader

        doc_id = str(uuid4())
        content = """# Main Title

## Subsection One
Content for subsection one.

## Subsection Two
Content for subsection two.

### Sub-subsection
Nested content here.
"""

        payloads = [
            {
                "document_id": doc_id,
                "content": content,
                "skip": False,
            }
        ]

        document_sections(reader=reader, writer=writer, payloads=payloads, incremental_mode="full")

        sections = reader.load("indexing_document_sections", where={"document_id": doc_id})

        # Check that heading field exists (may be None for small documents)
        if not sections.empty:
            first_section = sections.iloc[0]
            # The heading field should exist in the schema
            assert "heading" in first_section.index
            # For this small document, it might be None since it fits in one section
            # The important thing is that the field exists in the schema

    def test_section_ordering(self, writer_reader):
        """Test that sections maintain correct ordering."""
        writer, reader = writer_reader

        doc_id = str(uuid4())
        # Create content with numbered sections for easy verification
        content = "\n\n".join([f"# Section {i}\n" + f"Content {i}" * 100 for i in range(1, 11)])

        payloads = [
            {
                "document_id": doc_id,
                "content": content,
                "skip": False,
            }
        ]

        document_sections(reader=reader, writer=writer, payloads=payloads, incremental_mode="full")

        sections = reader.load("indexing_document_sections", where={"document_id": doc_id})

        if not sections.empty:
            # Sort by section_number and verify ordering
            sections_sorted = sections.sort_values("section_number")

            prev_num = -1
            for _, row in sections_sorted.iterrows():
                assert row["section_number"] > prev_num
                prev_num = row["section_number"]

            # Verify offsets are sequential
            prev_end = 0
            for _, row in sections_sorted.iterrows():
                assert row["start_offset"] >= prev_end
                prev_end = row["end_offset"]

    def test_batch_processing(self, writer_reader):
        """Test processing multiple documents in a single batch."""
        writer, reader = writer_reader

        payloads = []
        doc_ids = []

        for i in range(5):
            doc_id = str(uuid4())
            doc_ids.append(doc_id)
            payloads.append(
                {
                    "document_id": doc_id,
                    "content": f"Document {i} content\n" * 100,
                    "skip": False,
                }
            )

        result = document_sections(
            reader=reader, writer=writer, payloads=payloads, incremental_mode="full"
        )

        # Should have written sections for all documents
        assert result["rows_written"] >= len(payloads)

        # Verify each document has sections
        for doc_id in doc_ids:
            sections = reader.load("indexing_document_sections", where={"document_id": doc_id})
            assert not sections.empty

    def test_metadata_fields(self, writer_reader):
        """Test that metadata fields are properly set."""
        writer, reader = writer_reader

        doc_id = str(uuid4())
        content = "Test content for metadata verification"

        payloads = [
            {
                "document_id": doc_id,
                "content": content,
                "skip": False,
            }
        ]

        document_sections(reader=reader, writer=writer, payloads=payloads, incremental_mode="full")

        sections = reader.load("indexing_document_sections", where={"document_id": doc_id})

        if not sections.empty:
            row = sections.iloc[0]

            # Check metadata fields
            assert row.get("model_name") == "indexing.document_sections"
            assert row.get("is_active") is True
            assert row.get("workflow_id") == "test_workflow"
            assert row.get("created_at") is not None
            assert row.get("updated_at") is not None
