"""
Integration tests for workflows with the new models.
"""

from uuid import uuid4

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.workflows import run_section_splitting


class TestWorkflowIntegration:
    """Test the workflow integration with models."""

    def test_section_splitting_workflow(self, tmp_path):
        """Test the section splitting workflow end-to-end."""
        # Create temporary database
        db_path = tmp_path / "test.db"

        # Mock documents
        doc_id = str(uuid4())
        content = "This is test content for the workflow integration test."

        # Mock the framework's load_documents function
        import kurt.content.indexing_new.loaders as doc_loader

        original_load = doc_loader.load_documents

        def mock_load(filters, **kwargs):
            return [
                {
                    "document_id": doc_id,
                    "content": content,
                    "skip": False,
                }
            ]

        doc_loader.load_documents = mock_load

        # Also mock at the workflow import level since it imports from framework
        import kurt.content.indexing_new.workflows.workflow_indexing as workflow_module

        workflow_module.load_documents = mock_load

        # Configure the framework to use our test database
        import kurt.config

        original_config = kurt.config.get_config_or_default

        def mock_config():
            class MockConfig:
                PATH_DB = str(db_path)

                def get_absolute_sources_path(self):
                    return tmp_path / "sources"

            return MockConfig()

        kurt.config.get_config_or_default = mock_config

        try:
            # Run the workflow with explicit db_path
            filters = DocumentFilters()
            result = run_section_splitting(
                filters=filters,
                incremental_mode="full",
                workflow_id="test_workflow_integration",
                db_path=str(db_path),
            )

            # Check result
            assert "rows_written" in result
            assert result["rows_written"] >= 1

            # Verify data was written to database using TableReader
            from kurt.content.indexing_new.framework import TableReader

            reader = TableReader()
            df = reader.load("indexing_document_sections", where={"document_id": doc_id})

            assert len(df) >= 1
            assert df.iloc[0]["document_id"] == doc_id
            assert df.iloc[0]["workflow_id"] == "test_workflow_integration"

        finally:
            # Restore original functions
            doc_loader.load_documents = original_load
            workflow_module.load_documents = original_load
            kurt.config.get_config_or_default = original_config

    def test_section_splitting_workflow_incremental(self, tmp_path):
        """Test incremental mode skips unchanged documents."""
        # Create temporary database
        db_path = tmp_path / "test.db"

        # Mock documents - one that should be skipped
        doc_id = str(uuid4())

        # Mock the framework's load_documents function
        import kurt.content.indexing_new.loaders as doc_loader

        original_load = doc_loader.load_documents

        def mock_load(filters, incremental_mode="full", **kwargs):
            if incremental_mode == "delta":
                return [
                    {
                        "document_id": doc_id,
                        "content": "content",
                        "skip": True,
                        "skip_reason": "content_unchanged",
                    }
                ]
            else:
                return [
                    {
                        "document_id": doc_id,
                        "content": "content",
                        "skip": False,
                    }
                ]

        doc_loader.load_documents = mock_load

        # Also mock at the workflow import level
        import kurt.content.indexing_new.workflows.workflow_indexing as workflow_module

        workflow_module.load_documents = mock_load

        # Mock config
        import kurt.config

        original_config = kurt.config.get_config_or_default

        def mock_config():
            class MockConfig:
                PATH_DB = str(db_path)

                def get_absolute_sources_path(self):
                    return tmp_path / "sources"

            return MockConfig()

        kurt.config.get_config_or_default = mock_config

        try:
            # Run in delta mode with explicit db_path
            filters = DocumentFilters()
            result = run_section_splitting(
                filters=filters,
                incremental_mode="delta",
                workflow_id="test_incremental",
                db_path=str(db_path),
            )

            # Should have no rows written (document skipped)
            assert result.get("rows_written", 0) == 0

        finally:
            # Restore original functions
            doc_loader.load_documents = original_load
            workflow_module.load_documents = original_load
            kurt.config.get_config_or_default = original_config
