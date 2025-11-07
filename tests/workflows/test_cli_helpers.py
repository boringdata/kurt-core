"""
Unit tests for workflow CLI helpers.

Tests coverage:
- run_with_background_support() with different execution modes
- Background process spawning
- Environment variable passing (log file)
- Workflow ID checking
- Result unpickling and display
"""

import json
import subprocess
from unittest.mock import MagicMock, Mock, patch


class TestRunWithBackgroundSupport:
    """Tests for run_with_background_support() function."""

    def test_check_existing_workflow_by_id(self):
        """Should query and display workflow status when workflow_id is provided."""
        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_id = "abc12345"

        # Mock database query result
        mock_workflow = ("abc12345-full-id", "map_url_workflow", "SUCCESS", "output_data", None)

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                with patch("kurt.workflows.cli_helpers.console"):
                    run_with_background_support(
                        workflow_func=workflow_func, workflow_args={}, workflow_id=workflow_id
                    )

                # Verify SQL query was executed
                assert mock_ctx.execute.called

    def test_background_spawns_worker_process(self):
        """Should spawn detached worker process when background=True."""
        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_args = {"url": "https://example.com"}

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.workflows.map.get_map_queue"):
                with patch("subprocess.Popen") as mock_popen:
                    with patch("kurt.workflows.cli_helpers.console"):
                        run_with_background_support(
                            workflow_func=workflow_func,
                            workflow_args=workflow_args,
                            background=True,
                        )

        # Verify subprocess.Popen was called
        assert mock_popen.called

        # Verify process was started with correct detachment settings
        call_args = mock_popen.call_args
        assert call_args[1]["stdin"] == subprocess.DEVNULL
        assert call_args[1]["stdout"] == subprocess.DEVNULL
        assert call_args[1]["stderr"] == subprocess.DEVNULL
        assert call_args[1]["start_new_session"] is True

    def test_background_passes_workflow_id_file_env_var(self):
        """Should pass KURT_WORKFLOW_ID_FILE environment variable to worker."""
        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_args = {"url": "https://example.com"}

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.workflows.map.get_map_queue"):
                with patch("subprocess.Popen") as mock_popen:
                    with patch("kurt.workflows.cli_helpers.console"):
                        with patch("pathlib.Path.exists", return_value=False):
                            run_with_background_support(
                                workflow_func=workflow_func,
                                workflow_args=workflow_args,
                                background=True,
                            )

        # Verify environment variable was set
        call_args = mock_popen.call_args
        env = call_args[1]["env"]
        assert "KURT_WORKFLOW_ID_FILE" in env
        # Should be a temp file path
        assert env["KURT_WORKFLOW_ID_FILE"].endswith(".workflow_id")

    def test_background_command_arguments(self):
        """Should pass correct arguments to worker process."""
        import sys

        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="fetch_batch_workflow")
        workflow_args = {"identifiers": ["doc1", "doc2"], "fetch_engine": "trafilatura"}
        priority = 7

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.workflows.fetch.fetch_queue"):
                with patch("subprocess.Popen") as mock_popen:
                    with patch("kurt.workflows.cli_helpers.console"):
                        run_with_background_support(
                            workflow_func=workflow_func,
                            workflow_args=workflow_args,
                            background=True,
                            priority=priority,
                        )

        # Verify command arguments
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1] == "-m"
        assert call_args[2] == "kurt.workflows._worker"
        assert call_args[3] == "fetch_batch_workflow"
        assert json.loads(call_args[4]) == workflow_args
        assert call_args[5] == str(priority)

    def test_synchronous_returns_none_signal(self):
        """Should return None to signal caller to handle sync execution."""
        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_args = {"url": "https://example.com"}

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.workflows.cli_helpers.console"):
                result = run_with_background_support(
                    workflow_func=workflow_func, workflow_args=workflow_args, background=False
                )

        # Should return None to signal caller
        assert result is None


class TestWorkflowResultUnpickling:
    """Tests for unpickling workflow results from database."""

    def test_unpickles_base64_encoded_result(self):
        """Should unpickle base64-encoded workflow result."""
        import base64
        import pickle

        from kurt.workflows.cli_helpers import run_with_background_support

        # Create a sample result and pickle it
        original_result = {
            "url": "https://example.com",
            "total": 1,
            "new": 1,
            "existing": 0,
            "method": "crawl",
            "discovered": [{"url": "https://example.com/", "doc_id": "test-id", "created": True}],
        }

        pickled = pickle.dumps(original_result)
        encoded = base64.b64encode(pickled).decode("utf-8")

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_id = "test123"

        # Mock database query result with pickled output
        mock_workflow = ("test123-full", "map_url_workflow", "SUCCESS", encoded, None)

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                with patch("kurt.workflows.cli_helpers.console"):
                    result = run_with_background_support(
                        workflow_func=workflow_func, workflow_args={}, workflow_id=workflow_id
                    )

        # Verify result was unpickled correctly
        assert result == original_result

    def test_falls_back_to_json_parsing(self):
        """Should fall back to JSON parsing if unpickling fails."""
        from kurt.workflows.cli_helpers import run_with_background_support

        # Create a JSON result (not pickled)
        json_result = json.dumps({"status": "success", "count": 42})

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_id = "test456"

        mock_workflow = ("test456-full", "map_url_workflow", "SUCCESS", json_result, None)

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                with patch("kurt.workflows.cli_helpers.console"):
                    result = run_with_background_support(
                        workflow_func=workflow_func, workflow_args={}, workflow_id=workflow_id
                    )

        # Verify result was parsed as JSON
        assert result == {"status": "success", "count": 42}

    def test_handles_workflow_not_found(self):
        """Should handle case when workflow ID is not found."""
        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_id = "nonexistent"

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = None  # Not found
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                with patch("kurt.workflows.cli_helpers.console") as mock_console:
                    result = run_with_background_support(
                        workflow_func=workflow_func, workflow_args={}, workflow_id=workflow_id
                    )

        # Should return None for not found
        assert result is None

        # Should print error message
        assert any("not found" in str(call).lower() for call in mock_console.print.call_args_list)

    def test_handles_pending_workflow(self):
        """Should handle workflow that is still PENDING."""
        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_id = "pending123"

        mock_workflow = ("pending123-full", "map_url_workflow", "PENDING", None, None)

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.db.database.get_session") as mock_session:
                mock_ctx = MagicMock()
                mock_ctx.__enter__.return_value = mock_ctx
                mock_ctx.__exit__.return_value = None

                mock_result = Mock()
                mock_result.fetchone.return_value = mock_workflow
                mock_ctx.execute.return_value = mock_result

                mock_session.return_value = mock_ctx

                with patch("kurt.workflows.cli_helpers.console") as mock_console:
                    result = run_with_background_support(
                        workflow_func=workflow_func, workflow_args={}, workflow_id=workflow_id
                    )

        # Should return None for pending workflow
        assert result is None

        # Should print status message
        assert any("PENDING" in str(call) for call in mock_console.print.call_args_list)


class TestPriorityHandling:
    """Tests for priority parameter handling."""

    def test_default_priority_is_10(self):
        """Default priority should be 10."""

        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_args = {"url": "https://example.com"}

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.workflows.map.get_map_queue"):
                with patch("subprocess.Popen") as mock_popen:
                    with patch("kurt.workflows.cli_helpers.console"):
                        run_with_background_support(
                            workflow_func=workflow_func,
                            workflow_args=workflow_args,
                            background=True,
                            # No priority specified
                        )

        # Verify default priority of 10 was used
        call_args = mock_popen.call_args[0][0]
        assert call_args[5] == "10"

    def test_custom_priority_is_passed(self):
        """Custom priority should be passed to worker."""

        from kurt.workflows.cli_helpers import run_with_background_support

        workflow_func = Mock(__name__="map_url_workflow")
        workflow_args = {"url": "https://example.com"}
        priority = 1  # High priority

        with patch("kurt.workflows.cli_helpers.get_dbos"):
            with patch("kurt.workflows.map.get_map_queue"):
                with patch("subprocess.Popen") as mock_popen:
                    with patch("kurt.workflows.cli_helpers.console"):
                        run_with_background_support(
                            workflow_func=workflow_func,
                            workflow_args=workflow_args,
                            background=True,
                            priority=priority,
                        )

        # Verify custom priority was used
        call_args = mock_popen.call_args[0][0]
        assert call_args[5] == "1"
