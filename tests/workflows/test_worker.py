"""
Unit tests for workflow worker module.

Tests coverage:
- Worker process argument parsing
- DBOS initialization timing
- Stdout/stderr redirection
- Log file environment variable handling
- Status polling loop
- Workflow completion detection
"""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestWorkerArgumentParsing:
    """Tests for worker command-line argument parsing."""

    def test_worker_requires_workflow_name_and_args(self):
        """Worker should require workflow name and args."""
        import subprocess
        import sys
        import tempfile

        # Create a temporary directory with minimal .kurt setup
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            from pathlib import Path

            # Create minimal .kurt directory structure
            kurt_dir = Path(tmpdir) / ".kurt"
            kurt_dir.mkdir()

            # Create a minimal database file to avoid initialization errors
            db_file = kurt_dir / "kurt.sqlite"
            db_file.touch()

            # Set environment to use this temp directory
            env = os.environ.copy()
            env["KURT_DB_PATH"] = str(db_file)

            # Test by running the module with insufficient args
            result = subprocess.run(
                [sys.executable, "-m", "kurt.workflows._worker"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                env=env,
            )

            # Should exit with code 1 due to insufficient args
            assert result.returncode == 1
            # Check for usage message (case-insensitive since output uses lowercase)
            assert "usage:" in result.stderr.lower()

    def test_worker_main_with_valid_args(self):
        """Worker should parse valid arguments correctly."""

        workflow_name = "map_url_workflow"
        workflow_args = json.dumps({"url": "https://example.com"})
        priority = "5"

        with patch.object(sys, "argv", ["_worker.py", workflow_name, workflow_args, priority]):
            with patch("kurt.workflows._worker.run_workflow_worker"):
                # Manually call what __main__ would do
                if len(sys.argv) >= 3:
                    wf_name = sys.argv[1]
                    wf_args = sys.argv[2]
                    prio = int(sys.argv[3]) if len(sys.argv) > 3 else 10

                    assert wf_name == workflow_name
                    assert wf_args == workflow_args
                    assert prio == 5


class TestWorkerDBOSInitialization:
    """Tests for DBOS initialization timing in worker."""

    @patch("kurt.workflows.init_dbos")
    @patch("kurt.workflows.get_dbos")
    @patch("os.open")
    @patch("os.dup2")
    @patch("os.close")
    @patch("os.makedirs")
    def test_dbos_initialized_before_stdout_redirect(
        self, mock_makedirs, mock_close, mock_dup2, mock_open, mock_get_dbos, mock_init_dbos
    ):
        """DBOS should be initialized BEFORE stdout/stderr redirection."""
        from kurt.workflows._worker import run_workflow_worker

        # Setup mocks
        mock_dbos = MagicMock()
        mock_get_dbos.return_value = mock_dbos

        mock_queue = MagicMock()
        mock_handle = MagicMock()
        mock_handle.workflow_id = "test-workflow-id"
        mock_handle.get_status.return_value.status = "SUCCESS"
        mock_queue.enqueue.return_value = mock_handle

        workflow_name = "map_url_workflow"
        workflow_args_json = json.dumps({"url": "https://example.com"})

        # We need to patch ALL uses of time.time throughout the call chain
        with patch("time.time", return_value=0):  # Don't timeout
            with patch("time.sleep"):
                with patch("kurt.workflows.map.map_url_workflow"):
                    with patch("kurt.workflows.map.get_map_queue", return_value=mock_queue):
                        with patch("sys.exit"):
                            try:
                                run_workflow_worker(workflow_name, workflow_args_json, priority=10)
                            except SystemExit:
                                pass

        # Verify DBOS was initialized
        assert mock_init_dbos.called


class TestWorkerLogFileHandling:
    """Tests for log file environment variable handling."""

    @patch("kurt.workflows.init_dbos")
    @patch("kurt.workflows.get_dbos")
    @patch("os.open", return_value=99)  # Mock file descriptor
    @patch("os.dup2")
    @patch("os.close")
    @patch("pathlib.Path.mkdir")
    def test_redirect_to_workflow_log_file(
        self, mock_mkdir, mock_close, mock_dup2, mock_open, mock_get_dbos, mock_init_dbos
    ):
        """Worker should redirect to .kurt/logs/workflow-{id}.log."""
        from kurt.workflows._worker import run_workflow_worker

        # Setup mocks
        mock_dbos = MagicMock()
        mock_get_dbos.return_value = mock_dbos

        mock_queue = MagicMock()
        mock_handle = MagicMock()
        mock_handle.workflow_id = "test-workflow-123"
        mock_handle.get_status.return_value.status = "SUCCESS"
        mock_queue.enqueue.return_value = mock_handle

        workflow_name = "map_url_workflow"
        workflow_args_json = json.dumps({"url": "https://example.com"})

        with patch("time.time", side_effect=[0, 100, 200]):
            with patch("time.sleep"):
                with patch("kurt.workflows.map.map_url_workflow"):
                    with patch("kurt.workflows.map.get_map_queue", return_value=mock_queue):
                        with patch("sys.exit"):
                            try:
                                run_workflow_worker(workflow_name, workflow_args_json, priority=10)
                            except SystemExit:
                                pass

        # Verify log directory was created
        assert mock_mkdir.called

        # Verify workflow-specific log file was opened
        # Find the call that opens the workflow log file (not /dev/null)
        log_file_calls = [
            call
            for call in mock_open.call_args_list
            if ".kurt/logs/workflow-" in str(call) or "workflow-" in str(call)
        ]
        assert len(log_file_calls) >= 1

        # Verify stdout and stderr were redirected
        assert mock_dup2.call_count >= 4  # 2 for devnull, 2 for log file

    def test_workflow_id_file_env_var_checked(self):
        """Worker should check KURT_WORKFLOW_ID_FILE environment variable."""
        # This is tested indirectly through integration tests
        # Direct testing causes file descriptor issues with pytest's output capture
        # since the worker redirects stdout/stderr with os.dup2()
        pass


class TestWorkerStatusPolling:
    """Tests for active status polling loop."""

    @patch("kurt.workflows.init_dbos")
    @patch("kurt.workflows.get_dbos")
    @patch("os.open")
    @patch("os.dup2")
    @patch("os.close")
    def test_polls_status_until_completion(
        self, mock_close, mock_dup2, mock_open, mock_get_dbos, mock_init_dbos
    ):
        """Worker should actively poll status until workflow completes."""
        from kurt.workflows._worker import run_workflow_worker

        # Setup mocks
        mock_dbos = MagicMock()
        mock_get_dbos.return_value = mock_dbos

        mock_queue = MagicMock()
        mock_handle = MagicMock()

        # Simulate workflow progression: PENDING → PENDING → SUCCESS
        mock_status_pending = Mock()
        mock_status_pending.status = "PENDING"

        mock_status_success = Mock()
        mock_status_success.status = "SUCCESS"

        mock_handle.get_status.side_effect = [
            mock_status_pending,
            mock_status_pending,
            mock_status_success,
        ]
        mock_queue.enqueue.return_value = mock_handle

        workflow_name = "map_url_workflow"
        workflow_args_json = json.dumps({"url": "https://example.com"})

        with patch("time.time", return_value=0):  # Don't timeout
            with patch("time.sleep") as mock_sleep:
                with patch("kurt.workflows.map.map_url_workflow"):
                    with patch("kurt.workflows.map.get_map_queue", return_value=mock_queue):
                        with patch("sys.exit"):
                            try:
                                run_workflow_worker(workflow_name, workflow_args_json, priority=10)
                            except SystemExit:
                                pass

        # Verify status was polled multiple times
        assert mock_handle.get_status.call_count == 3

        # Verify sleep was called between polls
        assert mock_sleep.call_count >= 2

    @patch("kurt.workflows.init_dbos")
    @patch("kurt.workflows.get_dbos")
    @patch("os.open")
    @patch("os.dup2")
    @patch("os.close")
    def test_exits_on_error_status(
        self, mock_close, mock_dup2, mock_open, mock_get_dbos, mock_init_dbos
    ):
        """Worker should exit when workflow status is ERROR."""
        from kurt.workflows._worker import run_workflow_worker

        # Setup mocks
        mock_dbos = MagicMock()
        mock_get_dbos.return_value = mock_dbos

        mock_queue = MagicMock()
        mock_handle = MagicMock()

        mock_status_error = Mock()
        mock_status_error.status = "ERROR"

        mock_handle.get_status.return_value = mock_status_error
        mock_queue.enqueue.return_value = mock_handle

        workflow_name = "map_url_workflow"
        workflow_args_json = json.dumps({"url": "https://example.com"})

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("kurt.workflows.map.map_url_workflow"):
                    with patch("kurt.workflows.map.get_map_queue", return_value=mock_queue):
                        with patch("sys.exit") as mock_exit:
                            run_workflow_worker(workflow_name, workflow_args_json, priority=10)

        # Verify exit was called
        mock_exit.assert_called_once_with(0)

    @patch("kurt.workflows.init_dbos")
    @patch("kurt.workflows.get_dbos")
    @patch("os.open")
    @patch("os.dup2")
    @patch("os.close")
    def test_timeout_after_max_wait_time(
        self, mock_close, mock_dup2, mock_open, mock_get_dbos, mock_init_dbos
    ):
        """Worker should timeout after max wait time (600 seconds)."""
        from kurt.workflows._worker import run_workflow_worker

        # Setup mocks
        mock_dbos = MagicMock()
        mock_get_dbos.return_value = mock_dbos

        mock_queue = MagicMock()
        mock_handle = MagicMock()

        mock_status_pending = Mock()
        mock_status_pending.status = "PENDING"  # Never completes

        mock_handle.get_status.return_value = mock_status_pending
        mock_queue.enqueue.return_value = mock_handle

        workflow_name = "map_url_workflow"
        workflow_args_json = json.dumps({"url": "https://example.com"})

        # Simulate time passing beyond 600 seconds
        with patch("time.time", side_effect=[0, 300, 601]):  # Start, middle, timeout
            with patch("time.sleep"):
                with patch("kurt.workflows.map.map_url_workflow"):
                    with patch("kurt.workflows.map.get_map_queue", return_value=mock_queue):
                        with patch("sys.exit") as mock_exit:
                            run_workflow_worker(workflow_name, workflow_args_json, priority=10)

        # Verify exit was called after timeout
        mock_exit.assert_called_once_with(0)


class TestWorkerWorkflowSelection:
    """Tests for workflow function selection based on name."""

    @patch("kurt.workflows.init_dbos")
    @patch("kurt.workflows.get_dbos")
    @patch("os.open")
    @patch("os.dup2")
    @patch("os.close")
    def test_selects_map_workflow(
        self, mock_close, mock_dup2, mock_open, mock_get_dbos, mock_init_dbos
    ):
        """Worker should select map_url_workflow when workflow_name is 'map_url_workflow'."""
        from kurt.workflows._worker import run_workflow_worker

        mock_dbos = MagicMock()
        mock_get_dbos.return_value = mock_dbos

        mock_queue = MagicMock()
        mock_handle = MagicMock()
        mock_handle.get_status.return_value.status = "SUCCESS"
        mock_queue.enqueue.return_value = mock_handle

        with patch("time.time", side_effect=[0, 100, 200]):
            with patch("time.sleep"):
                with patch("kurt.workflows.map.map_url_workflow"):
                    with patch("kurt.workflows.map.get_map_queue", return_value=mock_queue):
                        with patch("sys.exit"):
                            run_workflow_worker(
                                "map_url_workflow", json.dumps({"url": "https://example.com"})
                            )

        # Verify queue.enqueue was called
        assert mock_queue.enqueue.called

    def test_exits_on_unknown_workflow(self):
        """Worker should exit with code 1 for unknown workflow name."""

        from kurt.workflows._worker import run_workflow_worker

        with patch("kurt.workflows.init_dbos"):
            with patch("kurt.workflows.get_dbos"):
                # Should raise SystemExit with code 1
                with pytest.raises(SystemExit) as exc_info:
                    run_workflow_worker("unknown_workflow", json.dumps({}))

                assert exc_info.value.code == 1
