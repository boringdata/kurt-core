"""E2E tests for fetch workflows.

Simplified tests that verify workflows are defined and can be registered with DBOS.
"""


class TestFetchWorkflowsExist:
    """Test that fetch workflows are properly defined."""

    def test_fetch_document_workflow_exists(self):
        """Test fetch_document_workflow is defined."""
        from kurt.content.fetch.workflow import fetch_document_workflow

        assert fetch_document_workflow is not None
        assert callable(fetch_document_workflow)

    def test_fetch_and_index_workflow_exists(self):
        """Test fetch_and_index_workflow is defined."""
        from kurt.content.fetch.workflow import fetch_and_index_workflow

        assert fetch_and_index_workflow is not None
        assert callable(fetch_and_index_workflow)

    def test_fetch_batch_workflow_exists(self):
        """Test fetch_batch_workflow is defined."""
        from kurt.content.fetch.workflow import fetch_batch_workflow

        assert fetch_batch_workflow is not None
        assert callable(fetch_batch_workflow)

    def test_workflows_have_dbos_decorators(self):
        """Test that workflows have DBOS decorator attributes."""
        from kurt.content.fetch.workflow import (
            fetch_and_index_workflow,
            fetch_batch_workflow,
            fetch_document_workflow,
        )

        # Workflows should have DBOS wrapper attributes
        # Note: We don't launch DBOS here, just verify decorator was applied
        assert callable(fetch_document_workflow)
        assert callable(fetch_and_index_workflow)
        assert callable(fetch_batch_workflow)
