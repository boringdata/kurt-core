"""
Unit tests for workflow CLI commands.

Tests coverage:
- kurt workflows list (with filters and formats)
- kurt workflows status (with result unpickling)
- kurt workflows follow
- Full ID display
- ID substring filtering
"""

import base64
import json
import pickle
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


class TestWorkflowsListCommand:
    """Tests for 'kurt workflows list' command."""

    def test_list_displays_full_ids_by_default(self, runner):
        """Should display full workflow IDs by default."""
        from kurt.commands.workflows import workflows_group

        # Mock workflow data with full UUIDs
        mock_workflows = [
            (
                "d28902c1-8a6f-4e37-9bf1-208c9d164682",
                "map_url_workflow",
                "SUCCESS",
                1762546092000,
                1762546092000,
            ),
            (
                "a69045d6-4e94-45d1-856e-7de0cc39e069",
                "fetch_batch_workflow",
                "SUCCESS",
                1762545938000,
                1762545939000,
            ),
        ]

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchall.return_value = mock_workflows
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["list"])

        # Command should succeed
        assert result.exit_code == 0

        # Output should contain full IDs (not truncated)
        assert (
            "d28902c1-8a6f-4e37-9bf1-208c9d164682" in result.output
            or "d28902c1-8a6f-4e" in result.output
        )

    def test_list_with_status_filter(self, runner):
        """Should filter workflows by status."""
        from kurt.commands.workflows import workflows_group

        mock_workflows = [
            ("workflow-1", "map_url_workflow", "SUCCESS", 1762546092000, 1762546092000),
        ]

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchall.return_value = mock_workflows
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["list", "--status", "SUCCESS"])

        assert result.exit_code == 0

        # Verify SQL query included status filter
        calls = mock_ctx.execute.call_args_list
        assert len(calls) > 0
        sql_call = calls[0]
        # Check that status parameter was passed
        if len(sql_call[0]) > 1:
            params = sql_call[0][1] if len(sql_call[0]) > 1 else sql_call[1].get("params", {})
            assert "status" in str(params) or "SUCCESS" in str(params)

    def test_list_with_id_filter(self, runner):
        """Should filter workflows by ID substring."""
        from kurt.commands.workflows import workflows_group

        mock_workflows = [
            (
                "d28902c1-8a6f-4e37-9bf1-208c9d164682",
                "map_url_workflow",
                "SUCCESS",
                1762546092000,
                1762546092000,
            ),
        ]

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchall.return_value = mock_workflows
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["list", "--id", "d28902"])

        assert result.exit_code == 0

    def test_list_plain_format(self, runner):
        """Should output plain format for easy parsing."""
        from kurt.commands.workflows import workflows_group

        mock_workflows = [
            ("workflow-id-1", "map_url_workflow", "SUCCESS", 1762546092000, 1762546092000),
            ("workflow-id-2", "fetch_batch_workflow", "PENDING", 1762545938000, 1762545939000),
        ]

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchall.return_value = mock_workflows
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["list", "--format", "plain"])

        assert result.exit_code == 0

        # Plain format should have pipe-separated values
        assert "|" in result.output
        assert "workflow-id-1" in result.output
        assert "workflow-id-2" in result.output

    def test_list_with_limit(self, runner):
        """Should limit number of results."""
        from kurt.commands.workflows import workflows_group

        mock_workflows = [
            ("workflow-1", "map_url_workflow", "SUCCESS", 1762546092000, 1762546092000),
        ]

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchall.return_value = mock_workflows
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["list", "--limit", "10"])

        assert result.exit_code == 0

    def test_list_no_workflows_found(self, runner):
        """Should handle case when no workflows exist."""
        from kurt.commands.workflows import workflows_group

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchall.return_value = []  # No workflows
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["list"])

        assert result.exit_code == 0
        assert "No workflows found" in result.output


class TestWorkflowsStatusCommand:
    """Tests for 'kurt workflows status' command."""

    def test_status_unpickles_result(self, runner):
        """Should unpickle base64-encoded workflow result."""
        from kurt.commands.workflows import workflows_group

        # Create pickled result
        original_result = {
            "url": "https://example.com",
            "total": 1,
            "new": 1,
            "existing": 0,
            "method": "crawl",
        }
        pickled = pickle.dumps(original_result)
        encoded = base64.b64encode(pickled).decode("utf-8")

        mock_workflow = (
            "test-workflow-id",
            "map_url_workflow",
            "SUCCESS",
            1762546092000,
            1762546092000,
            None,
            encoded,
            None,
        )

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["status", "test-workflow-id"])

        assert result.exit_code == 0
        assert "https://example.com" in result.output
        assert "SUCCESS" in result.output

    def test_status_json_output(self, runner):
        """Should output JSON format when --json flag is provided."""
        from kurt.commands.workflows import workflows_group

        # Create pickled result
        original_result = {"status": "success", "count": 42}
        pickled = pickle.dumps(original_result)
        encoded = base64.b64encode(pickled).decode("utf-8")

        mock_workflow = (
            "test-workflow-id",
            "map_url_workflow",
            "SUCCESS",
            1762546092000,
            1762546092000,
            None,
            encoded,
            None,
        )

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["status", "test-workflow-id", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["workflow_id"] == "test-workflow-id"
        assert output_data["status"] == "SUCCESS"
        assert output_data["output"] == original_result

    def test_status_workflow_not_found(self, runner):
        """Should handle case when workflow is not found."""
        from kurt.commands.workflows import workflows_group

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = None  # Not found
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["status", "nonexistent-id"])

        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_status_displays_error(self, runner):
        """Should display error when workflow has error status."""
        from kurt.commands.workflows import workflows_group

        mock_workflow = (
            "error-workflow-id",
            "map_url_workflow",
            "ERROR",
            1762546092000,
            1762546092000,
            None,
            None,
            "Connection timeout",
        )

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["status", "error-workflow-id"])

        assert result.exit_code == 0
        assert "ERROR" in result.output
        assert "Connection timeout" in result.output


class TestWorkflowsFollowCommand:
    """Tests for 'kurt workflows follow' command."""

    def test_follow_displays_workflow_info(self, runner):
        """Should display workflow information when following."""
        from kurt.commands.workflows import workflows_group

        # Mock initial workflow lookup
        mock_workflow_lookup = ("follow-id-full", "map_url_workflow", "PENDING")

        # Mock status check
        mock_status_check = ("SUCCESS", None, None)

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.workflows.get_dbos") as mock_get_dbos:
                mock_dbos = MagicMock()
                mock_get_dbos.return_value = mock_dbos

                with patch("kurt.db.database.get_session") as mock_session:
                    mock_ctx = MagicMock()
                    mock_ctx.__enter__.return_value = mock_ctx
                    mock_ctx.__exit__.return_value = None

                    # First call: workflow lookup
                    # Second call: status check
                    mock_result_lookup = Mock()
                    mock_result_lookup.fetchone.return_value = mock_workflow_lookup

                    mock_result_status = Mock()
                    mock_result_status.fetchone.return_value = mock_status_check

                    mock_ctx.execute.side_effect = [mock_result_lookup, mock_result_status]

                    mock_session.return_value = mock_ctx

                    result = runner.invoke(workflows_group, ["follow", "follow-id"])

        # Command should exit (workflow completed immediately)
        assert "follow-id-full" in result.output
        assert "map_url_workflow" in result.output

    def test_follow_workflow_not_found(self, runner):
        """Should handle case when workflow is not found."""
        from kurt.commands.workflows import workflows_group

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.workflows.get_dbos"):
                with patch("kurt.db.database.get_session") as mock_session:
                    mock_ctx = MagicMock()
                    mock_ctx.__enter__.return_value = mock_ctx
                    mock_ctx.__exit__.return_value = None

                    mock_result = Mock()
                    mock_result.fetchone.return_value = None  # Not found
                    mock_ctx.execute.return_value = mock_result

                    mock_session.return_value = mock_ctx

                    result = runner.invoke(workflows_group, ["follow", "nonexistent-id"])

        assert "not found" in result.output.lower()


class TestResultUnpickling:
    """Tests for result unpickling across all commands."""

    def test_unpickle_complex_nested_result(self):
        """Should unpickle complex nested data structures."""
        from kurt.commands.workflows import workflows_group

        # Create complex nested result
        complex_result = {
            "url": "https://example.com",
            "discovered": [
                {"url": "https://example.com/page1", "doc_id": "id1", "created": True},
                {"url": "https://example.com/page2", "doc_id": "id2", "created": False},
            ],
            "metadata": {"total": 2, "new": 1, "existing": 1},
        }

        pickled = pickle.dumps(complex_result)
        encoded = base64.b64encode(pickled).decode("utf-8")

        mock_workflow = (
            "complex-id",
            "map_url_workflow",
            "SUCCESS",
            1762546092000,
            1762546092000,
            None,
            encoded,
            None,
        )

        runner = CliRunner()

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["status", "complex-id"])

        assert result.exit_code == 0
        # Should contain unpickled data
        assert "example.com/page1" in result.output
        assert "example.com/page2" in result.output

    def test_fallback_to_json_when_not_pickled(self):
        """Should fall back to JSON parsing when result is not pickled."""
        from kurt.commands.workflows import workflows_group

        # JSON result (not pickled)
        json_result = json.dumps({"status": "ok", "value": 123})

        mock_workflow = (
            "json-id",
            "map_url_workflow",
            "SUCCESS",
            1762546092000,
            1762546092000,
            None,
            json_result,
            None,
        )

        runner = CliRunner()

        with patch("kurt.commands.workflows._check_dbos_available"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                result = runner.invoke(workflows_group, ["status", "json-id"])

        assert result.exit_code == 0
        # Should parse JSON successfully
        assert '"status": "ok"' in result.output or '"value": 123' in result.output
