"""E2E tests for complete indexing workflows.

Tests workflow orchestration with mocked extraction to avoid LLM dependencies.
"""

from unittest.mock import patch
from uuid import uuid4


class TestCompleteIndexingWorkflow:
    """Test complete_indexing_workflow (Stages 1-4)."""

    def test_workflow_orchestration(self, tmp_project, reset_dbos_state):
        """Test that workflow properly orchestrates extraction + entity resolution."""
        from dbos import DBOS

        from kurt.content.indexing.workflow_indexing import complete_indexing_workflow
        from kurt.workflows import init_dbos

        init_dbos()
        DBOS.launch()

        try:
            # Mock the extract step to return success
            with patch(
                "kurt.content.indexing.workflow_indexing.extract_documents_step"
            ) as mock_extract:
                mock_extract.return_value = {
                    "results": [
                        {
                            "document_id": str(uuid4()),
                            "kg_data": {
                                "new_entities": [],
                                "existing_entities": [],
                                "relationships": [],
                            },
                        }
                    ],
                    "succeeded": 1,
                    "failed": 0,
                    "skipped": 0,
                    "total": 1,
                }

                result = complete_indexing_workflow([str(uuid4())], force=True, enable_kg=True)

                # Verify extract step was called
                mock_extract.assert_called_once()

                # Check workflow returns expected structure
                assert "extract_results" in result
                assert "kg_stats" in result
                assert "workflow_id" in result

        finally:
            DBOS.destroy()

    def test_workflow_with_kg_disabled(self, tmp_project, reset_dbos_state):
        """Test workflow skips entity resolution when enable_kg=False."""
        from dbos import DBOS

        from kurt.content.indexing.workflow_indexing import complete_indexing_workflow
        from kurt.workflows import init_dbos

        init_dbos()
        DBOS.launch()

        try:
            # Mock extract to return success
            with patch(
                "kurt.content.indexing.workflow_indexing.extract_documents_step"
            ) as mock_extract:
                mock_extract.return_value = {
                    "results": [{"document_id": str(uuid4()), "kg_data": {}}],
                    "succeeded": 1,
                    "failed": 0,
                    "skipped": 0,
                    "total": 1,
                }

                result = complete_indexing_workflow([str(uuid4())], force=True, enable_kg=False)

                # Should skip entity resolution - kg_stats will be None when KG disabled
                assert (
                    result["kg_stats"] is None or result["kg_stats"].get("entities_created", 0) == 0
                )

        finally:
            DBOS.destroy()

    def test_workflow_handles_extraction_errors(self, tmp_project, reset_dbos_state):
        """Test workflow handles extraction failures gracefully."""
        from dbos import DBOS

        from kurt.content.indexing.workflow_indexing import complete_indexing_workflow
        from kurt.workflows import init_dbos

        init_dbos()
        DBOS.launch()

        try:
            # Mock extract to return failure
            with patch(
                "kurt.content.indexing.workflow_indexing.extract_documents_step"
            ) as mock_extract:
                mock_extract.return_value = {
                    "results": [],
                    "errors": [{"document_id": str(uuid4()), "error": "Test error"}],
                    "succeeded": 0,
                    "failed": 1,
                    "skipped": 0,
                    "total": 1,
                }

                result = complete_indexing_workflow([str(uuid4())], force=True, enable_kg=True)

                # Should handle error gracefully
                assert result["extract_results"]["failed"] == 1
                assert result["kg_stats"] is None  # No KG processing on failure

        finally:
            DBOS.destroy()
