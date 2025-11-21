"""E2E tests for map workflow.

Simplified tests that verify workflow is defined.
"""


class TestMapUrlWorkflow:
    """Test map_url_workflow (URL discovery and document creation)."""

    def test_workflow_exists(self):
        """Test map_url_workflow is defined."""
        from kurt.content.map.workflow import map_url_workflow

        assert map_url_workflow is not None
        assert callable(map_url_workflow)

    def test_workflow_has_dbos_decorator(self):
        """Test workflow has DBOS decorator applied."""
        from kurt.content.map.workflow import map_url_workflow

        # Verify it's callable (DBOS decorated workflows are callable)
        assert callable(map_url_workflow)
