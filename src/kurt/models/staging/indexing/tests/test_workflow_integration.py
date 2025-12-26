"""
Integration tests for workflows with the new models.

Tests the execute_model_sync and run_pipeline functions with real database.
"""

import pytest

from kurt.core import (
    ModelContext,
    PipelineConfig,
    PipelineContext,
)
from kurt.core.model_runner import execute_model_sync
from kurt.utils.filtering import DocumentFilters


class TestExecuteModelSync:
    """Test execute_model_sync for running models without DBOS."""

    def test_execute_document_sections_model(self, tmp_project, add_test_documents):
        """Test executing document_sections model via execute_model_sync."""
        content = "This is test content for the model execution test."

        doc_ids = add_test_documents(
            [
                {
                    "title": "Test Doc",
                    "content": content,
                    "source_url": "https://example.com/test-exec",
                }
            ]
        )

        ctx = PipelineContext(
            filters=DocumentFilters(ids=doc_ids[0]),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)

        assert "rows_written" in result
        assert result["rows_written"] == 1
        assert result["table_name"] == "staging_indexing_document_sections"

    def test_execute_model_with_skip(self, tmp_project, add_test_documents):
        """Test that documents without content don't produce output."""
        from kurt.db.documents import add_document

        # Add a document without content (stays NOT_FETCHED)
        doc_id = add_document("https://example.com/no-content")

        ctx = PipelineContext(
            filters=DocumentFilters(ids=str(doc_id)),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

        result = execute_model_sync("staging.indexing.document_sections", ctx)

        # Should have no rows written (document has no content)
        assert result.get("rows_written", 0) == 0

    def test_execute_model_not_found(self):
        """Test error handling when model is not in registry."""
        filters = DocumentFilters()
        ctx = ModelContext(filters=filters, workflow_id="test")

        with pytest.raises(ValueError) as exc_info:
            execute_model_sync("nonexistent.model", ctx)

        assert "not found in registry" in str(exc_info.value)


class TestPipelineConfig:
    """Test PipelineConfig dataclass."""

    def test_pipeline_config_defaults(self):
        """Test default values for PipelineConfig."""
        pipeline = PipelineConfig(name="test_pipeline", models=["model.one", "model.two"])

        assert pipeline.name == "test_pipeline"
        assert pipeline.stop_on_error is True
        assert len(pipeline.models) == 2

    def test_pipeline_config_custom(self):
        """Test custom values for PipelineConfig."""
        pipeline = PipelineConfig(
            name="my_pipeline",
            models=["a", "b", "c"],
            stop_on_error=False,
        )

        assert pipeline.name == "my_pipeline"
        assert pipeline.stop_on_error is False
        assert pipeline.models == ["a", "b", "c"]


class TestModelContext:
    """Test ModelContext dataclass."""

    def test_model_context_defaults(self):
        """Test default values for ModelContext."""
        filters = DocumentFilters()
        ctx = ModelContext(filters=filters)

        assert ctx.incremental_mode == "full"
        assert ctx.workflow_id is None
        assert ctx.metadata == {}

    def test_model_context_metadata(self):
        """Test that metadata is passed through."""
        filters = DocumentFilters()
        ctx = ModelContext(
            filters=filters,
            workflow_id="test_wf",
            metadata={"key": "value"},
        )

        assert ctx.metadata == {"key": "value"}


class TestIndexingPipeline:
    """Test the INDEXING_PIPELINE configuration."""

    def test_indexing_pipeline_definition(self):
        """Test that indexing pipeline can be discovered from registered models."""
        # Ensure models are registered
        import kurt.models.staging.indexing  # noqa: F401
        from kurt.core import PipelineConfig

        # The staging models use "staging." prefix
        pipeline = PipelineConfig.discover("staging")

        assert pipeline.name == "staging"
        assert len(pipeline.models) >= 1
        assert "staging.indexing.document_sections" in pipeline.models
