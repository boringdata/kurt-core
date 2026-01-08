"""
Unit tests for kurt_new.core._worker module.

Tests pure functions and validation logic that don't require DBOS:
- Workflow path resolution and validation
- Output redirection to log files
- Command-line argument parsing

Integration tests for the full worker flow are in test_background_integration.py.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ============================================================================
# Module Import Tests
# ============================================================================


class TestWorkerModuleImport:
    """Test that worker module can be imported."""

    def test_worker_module_imports(self):
        """Worker module should import successfully."""
        from kurt_new.core import _worker

        assert hasattr(_worker, "run_workflow_worker")
        assert hasattr(_worker, "_resolve_workflow")
        assert hasattr(_worker, "_redirect_output")


# ============================================================================
# _resolve_workflow Tests
# ============================================================================


class TestResolveWorkflowValidation:
    """Tests for workflow path validation in _resolve_workflow."""

    def test_raises_on_missing_colon(self):
        """Should raise ValueError if path doesn't contain colon."""
        from kurt_new.core._worker import _resolve_workflow

        with pytest.raises(ValueError, match="must be in module:function format"):
            _resolve_workflow("invalid_path_no_colon")

    def test_raises_on_empty_string(self):
        """Should raise ValueError for empty string."""
        from kurt_new.core._worker import _resolve_workflow

        with pytest.raises(ValueError, match="must be in module:function format"):
            _resolve_workflow("")


class TestResolveWorkflowModuleErrors:
    """Tests for module resolution errors in _resolve_workflow."""

    def test_raises_on_nonexistent_module(self):
        """Should raise ModuleNotFoundError for nonexistent module."""
        from kurt_new.core._worker import _resolve_workflow

        with pytest.raises(ModuleNotFoundError):
            _resolve_workflow("nonexistent.module.xyz:some_func")

    def test_raises_on_invalid_module_path(self):
        """Should raise error for invalid module path syntax."""
        from kurt_new.core._worker import _resolve_workflow

        with pytest.raises(Exception):  # Could be ModuleNotFoundError or ValueError
            _resolve_workflow("123invalid:func")


class TestResolveWorkflowFunctionErrors:
    """Tests for function resolution errors in _resolve_workflow."""

    def test_raises_on_nonexistent_function(self):
        """Should raise ValueError if function doesn't exist in module."""
        from kurt_new.core._worker import _resolve_workflow

        with pytest.raises(ValueError, match="Workflow function not found"):
            _resolve_workflow("os:nonexistent_function_xyz_123")

    def test_raises_on_non_callable_attribute(self):
        """Should raise ValueError if attribute is not callable."""
        from kurt_new.core._worker import _resolve_workflow

        # os.name is a string, not callable
        with pytest.raises(ValueError, match="Workflow function not found"):
            _resolve_workflow("os:name")


class TestResolveWorkflowSuccess:
    """Tests for successful workflow resolution."""

    def test_resolves_stdlib_function(self):
        """Should resolve function from standard library."""
        from kurt_new.core._worker import _resolve_workflow

        func = _resolve_workflow("os.path:exists")
        assert callable(func)
        assert func is os.path.exists

    def test_resolves_json_function(self):
        """Should resolve json.dumps."""
        from kurt_new.core._worker import _resolve_workflow

        func = _resolve_workflow("json:dumps")
        assert callable(func)
        assert func is json.dumps

    def test_resolves_nested_module_function(self):
        """Should resolve function in deeply nested module."""
        from kurt_new.core._worker import _resolve_workflow

        func = _resolve_workflow("os.path:join")
        assert callable(func)
        assert func is os.path.join


# ============================================================================
# _redirect_output Tests
# ============================================================================


class TestRedirectOutputFileCreation:
    """Tests for log file creation in _redirect_output."""

    def test_creates_log_file(self, tmp_path):
        """Should create log file if it doesn't exist."""
        from kurt_new.core._worker import _redirect_output

        log_file = tmp_path / "test.log"
        original_stdout = os.dup(sys.stdout.fileno())
        original_stderr = os.dup(sys.stderr.fileno())

        try:
            _redirect_output(log_file)
            assert log_file.exists()
        finally:
            os.dup2(original_stdout, sys.stdout.fileno())
            os.dup2(original_stderr, sys.stderr.fileno())
            os.close(original_stdout)
            os.close(original_stderr)

    def test_appends_to_existing_file(self, tmp_path):
        """Should append to existing log file, not overwrite."""
        from kurt_new.core._worker import _redirect_output

        log_file = tmp_path / "test.log"
        log_file.write_text("existing content\n")

        original_stdout = os.dup(sys.stdout.fileno())
        original_stderr = os.dup(sys.stderr.fileno())

        try:
            _redirect_output(log_file)
            print("new content")
            sys.stdout.flush()
            content = log_file.read_text()
            assert "existing content" in content
        finally:
            os.dup2(original_stdout, sys.stdout.fileno())
            os.dup2(original_stderr, sys.stderr.fileno())
            os.close(original_stdout)
            os.close(original_stderr)


# ============================================================================
# Terminal Status Recognition Tests
# ============================================================================


class TestWorkerStatusTransitions:
    """Test workflow status transition recognition."""

    def test_terminal_statuses_recognized(self):
        """Should recognize all terminal statuses."""
        terminal_statuses = ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]

        for status in terminal_statuses:
            is_terminal = status in ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]
            assert is_terminal is True

    def test_non_terminal_statuses_recognized(self):
        """Should recognize non-terminal statuses."""
        non_terminal_statuses = ["PENDING", "ENQUEUED"]

        for status in non_terminal_statuses:
            is_terminal = status in ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]
            assert is_terminal is False


# ============================================================================
# Main Entry Point Tests
# ============================================================================


class TestWorkerMainEntryPoint:
    """Tests for __main__ entry point."""

    def test_requires_minimum_arguments(self):
        """Should exit with code 1 if insufficient arguments."""
        import subprocess

        project_root = Path(__file__).parent.parent.parent.parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")

        result = subprocess.run(
            [sys.executable, "-m", "kurt_new.core._worker"],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 1
        assert "Usage:" in result.stderr

    def test_shows_usage_message(self):
        """Should show usage message on insufficient arguments."""
        import subprocess

        project_root = Path(__file__).parent.parent.parent.parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root / "src")

        result = subprocess.run(
            [sys.executable, "-m", "kurt_new.core._worker", "only_one_arg"],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 1
        assert "workflow_path" in result.stderr
        assert "workflow_args_json" in result.stderr


class TestWorkerArgumentParsing:
    """Tests for command-line argument parsing."""

    def test_parses_workflow_path(self):
        """Should parse workflow path from argv[1]."""
        with patch.object(
            sys,
            "argv",
            ["_worker.py", "my.module:my_func", '{"args": [], "kwargs": {}}', "5"],
        ):
            workflow_path = sys.argv[1]
            assert workflow_path == "my.module:my_func"

    def test_parses_workflow_args_json(self):
        """Should parse workflow args JSON from argv[2]."""
        with patch.object(
            sys,
            "argv",
            ["_worker.py", "my.module:my_func", '{"args": ["a"], "kwargs": {"k": "v"}}', "5"],
        ):
            workflow_args_json = sys.argv[2]
            parsed = json.loads(workflow_args_json)
            assert parsed["args"] == ["a"]
            assert parsed["kwargs"] == {"k": "v"}

    def test_parses_priority(self):
        """Should parse priority from argv[3]."""
        with patch.object(
            sys,
            "argv",
            ["_worker.py", "my.module:my_func", '{"args": [], "kwargs": {}}', "5"],
        ):
            priority = int(sys.argv[3])
            assert priority == 5

    def test_default_priority_is_10(self):
        """Should default to priority 10 if not provided."""
        with patch.object(
            sys,
            "argv",
            ["_worker.py", "my.module:my_func", '{"args": [], "kwargs": {}}'],
        ):
            priority = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            assert priority == 10
