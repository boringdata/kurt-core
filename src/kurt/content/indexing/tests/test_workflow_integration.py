"""
Integration tests for workflows with the new models.

Tests the execute_model_sync and run_pipeline functions with mocked dependencies.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.core import (
    ModelContext,
    PipelineConfig,
    PipelineContext,
    TableWriter,
)


class TestExecuteModelSync:
    """Test execute_model_sync for running models without DBOS."""

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

    def test_execute_document_sections_model(self, mock_ctx):
        """Test executing document_sections model via the model function directly."""
        from kurt.content.indexing.step_document_sections import document_sections

        doc_id = str(uuid4())
        content = "This is test content for the model execution test."

        # Create mock reference
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

        # Mock writer
        mock_writer = MagicMock(spec=TableWriter)
        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_document_sections",
        }

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        assert "rows_written" in result
        assert result["rows_written"] == 1
        mock_writer.write.assert_called_once()

        # Verify the row was created correctly
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) >= 1
        assert rows[0].document_id == doc_id

    def test_execute_model_with_skip(self, mock_ctx):
        """Test that skipped documents don't produce output."""
        from kurt.content.indexing.step_document_sections import document_sections

        doc_id = str(uuid4())

        mock_documents = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "title": "Test Doc",
                    "content": "Content",
                    "skip": True,
                    "error": None,
                }
            ]
        )

        mock_writer = MagicMock(spec=TableWriter)

        result = document_sections(ctx=mock_ctx, documents=mock_documents, writer=mock_writer)

        # Should have no rows written (document skipped)
        assert result.get("rows_written", 0) == 0
        mock_writer.write.assert_not_called()

    def test_execute_model_not_found(self):
        """Test error handling when model is not in registry."""
        from kurt.core import execute_model_sync

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
        import kurt.content.indexing  # noqa: F401
        from kurt.core import PipelineConfig

        pipeline = PipelineConfig.discover("indexing")

        assert pipeline.name == "indexing"
        assert len(pipeline.models) >= 2
        assert "indexing.document_sections" in pipeline.models
