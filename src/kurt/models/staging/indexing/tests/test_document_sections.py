"""
Comprehensive unit tests for the document_sections model.

Tests section splitting, skip behavior, section hashing, and edge cases.
Uses tmp_project fixture for real database isolation.
"""

from kurt.core import PipelineContext, configure_dbos_writer
from kurt.core.model_runner import execute_model_sync
from kurt.models.staging.indexing.step_document_sections import (
    DocumentSectionRow,
    DocumentSectionsConfig,
)
from kurt.utils.filtering import DocumentFilters


class TestDocumentSectionsModel:
    """Test suite for the document_sections model."""

    def test_single_small_section(self, tmp_project, add_test_documents):
        """Test document that fits in a single section."""
        content = "This is a short document that fits in a single section."

        # Configure DBOS writer
        configure_dbos_writer(workflow_id="test-single-section")

        doc_ids = add_test_documents(
            [
                {
                    "title": "Test Doc",
                    "content": content,
                    "source_url": "https://example.com/test1",
                }
            ]
        )

        ctx = PipelineContext(
            filters=DocumentFilters(ids=doc_ids[0]),
            workflow_id="test-single-section",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)

        assert result["rows_written"] == 1
        assert result["table_name"] == "staging_indexing_document_sections"

    def test_multiple_sections_with_overlap(self, tmp_project, add_test_documents):
        """Test document split into multiple sections with overlap."""
        # Create content that will span multiple sections (default max is 5000 chars)
        max_chars = 5000
        content = "# Section One\n\n" + "A" * (max_chars - 100)
        content += "\n\n# Section Two\n\n" + "B" * (max_chars - 100)
        content += "\n\n# Section Three\n\n" + "C" * 500

        doc_ids = add_test_documents(
            [
                {
                    "title": "Test Doc",
                    "content": content,
                    "source_url": "https://example.com/test2",
                }
            ]
        )

        ctx = PipelineContext(
            filters=DocumentFilters(ids=doc_ids[0]),
            workflow_id="test-workflow",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)

        # Should create multiple sections
        assert result["rows_written"] >= 2

    def test_skip_not_fetched_documents(self, tmp_project, add_test_documents):
        """Test that documents without content (NOT_FETCHED) are skipped."""
        from kurt.db.documents import add_document

        # Add a document without setting content (stays NOT_FETCHED)
        doc_id = add_document("https://example.com/not-fetched")

        ctx = PipelineContext(
            filters=DocumentFilters(ids=str(doc_id)),
            workflow_id="test-workflow",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)

        # Should not write any rows - document has no content
        assert result["rows_written"] == 0

    def test_empty_content_handling(self, tmp_project, add_test_documents):
        """Test handling of documents with empty content."""
        doc_ids = add_test_documents(
            [
                {
                    "title": "Empty Doc",
                    "content": "",  # Empty content
                    "source_url": "https://example.com/empty",
                }
            ]
        )

        ctx = PipelineContext(
            filters=DocumentFilters(ids=doc_ids[0]),
            workflow_id="test-workflow",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)

        # Should not write any sections for empty content
        assert result["rows_written"] == 0

    def test_batch_processing(self, tmp_project, add_test_documents):
        """Test processing multiple documents in a single batch."""
        documents = [
            {
                "title": f"Doc {i}",
                "content": f"Document {i} content\n" * 100,
                "source_url": f"https://example.com/doc{i}",
            }
            for i in range(5)
        ]

        doc_ids = add_test_documents(documents)

        ctx = PipelineContext(
            filters=DocumentFilters(ids=",".join(doc_ids)),
            workflow_id="test-workflow",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)

        # Should have written sections for all documents
        assert result["rows_written"] >= len(documents)

    def test_section_hash_computed(self, tmp_project, add_test_documents):
        """Test that section hashes are computed."""
        doc_ids = add_test_documents(
            [
                {
                    "title": "Test Doc",
                    "content": "Test content for hash computation",
                    "source_url": "https://example.com/hash-test",
                }
            ]
        )

        ctx = PipelineContext(
            filters=DocumentFilters(ids=doc_ids[0]),
            workflow_id="test-workflow",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)
        assert result["rows_written"] == 1

        # Check the section has a hash
        from kurt.db.database import get_session

        session = get_session()
        section = session.query(DocumentSectionRow).first()
        assert section is not None
        assert section.section_hash  # Hash should be computed
        session.close()

    def test_document_title_preserved(self, tmp_project, add_test_documents):
        """Test that document title is preserved in sections."""
        doc_ids = add_test_documents(
            [
                {
                    "title": "My Important Document",
                    "content": "Test content for title verification",
                    "source_url": "https://example.com/title-test",
                }
            ]
        )

        ctx = PipelineContext(
            filters=DocumentFilters(ids=doc_ids[0]),
            workflow_id="test-workflow",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)
        assert result["rows_written"] == 1

        # Check the section has the document title
        from kurt.db.database import get_session

        session = get_session()
        section = session.query(DocumentSectionRow).first()
        assert section is not None
        assert section.document_title == "My Important Document"
        session.close()

    def test_empty_filters_processes_all(self, tmp_project, add_test_documents):
        """Test that empty filters processes all documents."""
        add_test_documents(
            [
                {
                    "title": "Doc 1",
                    "content": "Content 1",
                    "source_url": "https://example.com/all1",
                },
                {
                    "title": "Doc 2",
                    "content": "Content 2",
                    "source_url": "https://example.com/all2",
                },
            ]
        )

        # Empty filters = process all
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)

        # Should process both documents
        assert result["rows_written"] >= 2

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

    def test_config_schema_registered(self):
        """Test that DocumentSectionsConfig is properly configured."""
        config = DocumentSectionsConfig()

        # Check default values (accessing attribute gives the actual value)
        assert config.max_section_chars == 5000
        assert config.overlap_chars == 200
        assert config.min_section_size == 500

    def test_model_registered(self):
        """Test that the model is registered in ModelRegistry."""
        # Import to register
        import kurt.models.staging.indexing  # noqa: F401
        from kurt.core import ModelRegistry

        model_info = ModelRegistry.get("staging.indexing.document_sections")
        assert model_info is not None
        assert model_info["name"] == "staging.indexing.document_sections"

    def test_section_row_schema(self):
        """Test DocumentSectionRow schema fields."""
        row = DocumentSectionRow(
            document_id="test-doc-123",
            section_id="sec-1",
            section_number=1,
            content="Test content",
            start_offset=0,
            end_offset=12,
            document_title="Test Title",
        )

        assert row.document_id == "test-doc-123"
        assert row.section_id == "sec-1"
        assert row.section_number == 1
        assert row.content == "Test content"
        assert row.start_offset == 0
        assert row.end_offset == 12
        assert row.document_title == "Test Title"
        assert row.section_hash  # Auto-computed

    def test_section_row_table_name(self):
        """Test DocumentSectionRow table name."""
        assert DocumentSectionRow.__tablename__ == "staging_indexing_document_sections"
