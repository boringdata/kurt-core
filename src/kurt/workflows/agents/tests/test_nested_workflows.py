"""Tests for nested workflow functionality (parent-child relationships)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


class TestRunnerParentWorkflowId:
    """Tests for parent workflow ID handling in runner.py."""

    def test_store_parent_workflow_id_with_env_var(self):
        """Test that parent_workflow_id is stored when env var is set."""
        from kurt.core.runner import _store_parent_workflow_id

        with patch.dict(os.environ, {"KURT_PARENT_WORKFLOW_ID": "parent-123"}):
            with patch("kurt.core.runner.DBOS") as mock_dbos:
                _store_parent_workflow_id()

                mock_dbos.set_event.assert_called_once_with("parent_workflow_id", "parent-123")

    def test_store_parent_workflow_id_without_env_var(self):
        """Test that nothing happens when env var is not set."""
        from kurt.core.runner import _store_parent_workflow_id

        # Ensure env var is not set
        env = os.environ.copy()
        env.pop("KURT_PARENT_WORKFLOW_ID", None)

        with patch.dict(os.environ, env, clear=True):
            with patch("kurt.core.runner.DBOS") as mock_dbos:
                _store_parent_workflow_id()

                mock_dbos.set_event.assert_not_called()

    def test_store_parent_workflow_id_handles_error(self):
        """Test that errors in DBOS.set_event don't propagate."""
        from kurt.core.runner import _store_parent_workflow_id

        with patch.dict(os.environ, {"KURT_PARENT_WORKFLOW_ID": "parent-123"}):
            with patch("kurt.core.runner.DBOS") as mock_dbos:
                mock_dbos.set_event.side_effect = Exception("DBOS error")

                # Should not raise
                _store_parent_workflow_id()

    def test_run_workflow_calls_store_parent(self):
        """Test that run_workflow calls _store_parent_workflow_id."""
        from kurt.core.runner import run_workflow

        mock_workflow_func = MagicMock()
        mock_handle = MagicMock()
        mock_handle.get_result.return_value = {"result": "success"}

        with patch("kurt.core.runner.init_dbos"):
            with patch("kurt.core.runner.DBOS") as mock_dbos:
                mock_dbos.start_workflow.return_value = mock_handle
                with patch("kurt.core.runner._store_parent_workflow_id") as mock_store:
                    with patch("kurt.core.display.set_display_enabled"):
                        run_workflow(mock_workflow_func, "arg1", background=False)

                mock_store.assert_called_once()


class TestWorkerParentWorkflowId:
    """Tests for parent workflow ID handling in _worker.py."""

    def test_worker_store_parent_workflow_id_with_env_var(self):
        """Test that worker stores parent_workflow_id when env var is set."""
        from kurt.core._worker import _store_parent_workflow_id

        with patch.dict(os.environ, {"KURT_PARENT_WORKFLOW_ID": "parent-456"}):
            with patch("kurt.core._worker.DBOS") as mock_dbos:
                _store_parent_workflow_id()

                mock_dbos.set_event.assert_called_once_with("parent_workflow_id", "parent-456")

    def test_worker_store_parent_workflow_id_without_env_var(self):
        """Test that worker does nothing when env var is not set."""
        from kurt.core._worker import _store_parent_workflow_id

        env = os.environ.copy()
        env.pop("KURT_PARENT_WORKFLOW_ID", None)

        with patch.dict(os.environ, env, clear=True):
            with patch("kurt.core._worker.DBOS") as mock_dbos:
                _store_parent_workflow_id()

                mock_dbos.set_event.assert_not_called()


class TestExecutorParentWorkflowId:
    """Tests for parent workflow ID being set by executor."""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_executor_sets_parent_workflow_id_env(self, mock_run, mock_which, tmp_path):
        """Test that executor sets KURT_PARENT_WORKFLOW_ID env var when run_id is provided."""
        from kurt.workflows.agents.executor import agent_execution_step

        mock_which.return_value = "/usr/bin/claude"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"num_turns": 1, "result": "done"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch(
            "kurt.workflows.agents.executor._create_tool_tracking_settings"
        ) as mock_create:
            settings_file = tmp_path / "settings.json"
            tool_log_file = tmp_path / "tools.jsonl"
            settings_file.write_text("{}")
            tool_log_file.write_text("")
            mock_create.return_value = (str(settings_file), str(tool_log_file))

            with patch("kurt.workflows.agents.executor._get_project_root") as mock_root:
                mock_root.return_value = str(tmp_path)

                # Pass run_id to agent_execution_step
                agent_execution_step(
                    prompt="Test",
                    model="claude-sonnet-4-20250514",
                    max_turns=5,
                    allowed_tools=["Bash"],
                    run_id="workflow-789",
                )

        # Verify subprocess was called with correct env
        call_args = mock_run.call_args
        env = call_args[1]["env"]
        assert env["KURT_PARENT_WORKFLOW_ID"] == "workflow-789"


class TestApiParentWorkflowId:
    """Tests for parent_workflow_id in web API."""

    @pytest.fixture(autouse=True)
    def skip_without_fastapi(self):
        """Skip API tests if fastapi is not installed."""
        pytest.importorskip("fastapi")

    def test_decode_dbos_event_value(self):
        """Test decoding DBOS event values."""
        import base64
        import pickle

        from kurt.web.api.server import _decode_dbos_event_value

        # Encode a test value
        test_value = "parent-workflow-123"
        encoded = base64.b64encode(pickle.dumps(test_value)).decode()

        result = _decode_dbos_event_value(encoded)
        assert result == test_value

    def test_decode_dbos_event_value_none(self):
        """Test decoding None value."""
        from kurt.web.api.server import _decode_dbos_event_value

        result = _decode_dbos_event_value(None)
        assert result is None

    def test_decode_dbos_event_value_invalid(self):
        """Test decoding invalid value returns None."""
        from kurt.web.api.server import _decode_dbos_event_value

        result = _decode_dbos_event_value("not-valid-base64-pickle")
        assert result is None
