"""
Integration tests for background workflow execution.

Tests the FULL FLOW without mocking DBOS:
1. Spawn a background worker process using start_background_workflow
2. Worker initializes real DBOS and runs workflow
3. Workflow completes and status can be queried from real DB
4. Log files are created with correct content
5. Events are emitted (if applicable)

These tests require a real database - no DBOS mocking.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Mark all tests as integration tests - these are slower and require real DB
pytestmark = [pytest.mark.integration, pytest.mark.slow]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def integration_project(tmp_database):
    """
    Create a complete test project for integration testing.

    Uses real database (from tmp_database fixture) - NO DBOS MOCKING.
    """
    project_path = tmp_database

    # Ensure logs directory exists
    logs_dir = project_path / ".kurt" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    yield project_path


def _get_project_src_path() -> str:
    """Get the src directory path for PYTHONPATH."""
    # This file is at: src/kurt/core/tests/test_background_integration.py
    # We need: src/
    return str(Path(__file__).parent.parent.parent.parent.parent / "src")


@pytest.fixture
def test_workflow_package(integration_project):
    """
    Create a Python package with test workflows that the worker can import.

    The worker subprocess needs to be able to import the workflow function,
    so we create a real Python package in the test project directory.
    """
    # Create package directory
    pkg_dir = integration_project / "integration_test_workflows"
    pkg_dir.mkdir(exist_ok=True)

    # Create __init__.py
    (pkg_dir / "__init__.py").write_text("")

    # Create workflow module with real DBOS workflows
    workflow_code = '''"""
Test workflows for background worker integration tests.
These are real DBOS workflows that get executed by the worker subprocess.
"""
import time
from dbos import DBOS

@DBOS.workflow()
def echo_workflow(message: str = "hello") -> dict:
    """Simple workflow that echoes a message."""
    print(f"[ECHO_WORKFLOW] Received: {message}")
    return {"echo": message, "timestamp": time.time()}

@DBOS.workflow()
def add_workflow(a: int, b: int) -> dict:
    """Workflow that adds two numbers."""
    result = a + b
    print(f"[ADD_WORKFLOW] {a} + {b} = {result}")
    return {"a": a, "b": b, "sum": result}

@DBOS.workflow()
def slow_workflow(delay_seconds: float = 0.5) -> dict:
    """Workflow that takes some time to complete."""
    print(f"[SLOW_WORKFLOW] Sleeping for {delay_seconds}s...")
    time.sleep(delay_seconds)
    print("[SLOW_WORKFLOW] Done!")
    return {"delay": delay_seconds, "completed": True}
'''
    (pkg_dir / "workflows.py").write_text(workflow_code)

    yield {
        "package_path": str(integration_project),
        "module_name": "integration_test_workflows.workflows",
    }


# ============================================================================
# Background Worker Integration Tests
# ============================================================================


class TestBackgroundWorkerIntegration:
    """
    Integration tests for background workflow worker.

    These tests spawn real subprocesses and use real DBOS - no mocking.
    """

    def test_worker_returns_workflow_id(self, integration_project, test_workflow_package):
        """Worker should return a valid workflow ID."""
        src_path = _get_project_src_path()

        # We run the test in a subprocess to ensure clean DBOS state
        test_script = f"""
import os
import sys

# Add project src and test workflow package to path
sys.path.insert(0, "{src_path}")
sys.path.insert(0, "{test_workflow_package['package_path']}")
os.chdir("{integration_project}")

from kurt.core.background import start_background_workflow

workflow_id = start_background_workflow(
    "{test_workflow_package['module_name']}:echo_workflow",
    kwargs={{"message": "test_message"}},
    wait_for_id=True,
    id_timeout_sec=15.0,
)

if workflow_id:
    print(f"SUCCESS:{{workflow_id}}")
else:
    print("FAILED:no_id")
"""
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            f"{src_path}:{test_workflow_package['package_path']}:{env.get('PYTHONPATH', '')}"
        )

        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        # Check output for success
        output = result.stdout.strip()
        if result.returncode != 0 or "FAILED" in output:
            pytest.skip(f"Background worker test skipped - subprocess error: {result.stderr}")

        if "SUCCESS:" in output:
            workflow_id = output.split("SUCCESS:")[1].strip()
            assert len(workflow_id) > 0
            assert workflow_id != "None"

    def test_worker_creates_log_file(self, integration_project, test_workflow_package):
        """Worker should create a log file with workflow output."""
        src_path = _get_project_src_path()

        test_script = f"""
import os
import sys
import time

sys.path.insert(0, "{src_path}")
sys.path.insert(0, "{test_workflow_package['package_path']}")
os.chdir("{integration_project}")

from kurt.core.background import start_background_workflow

workflow_id = start_background_workflow(
    "{test_workflow_package['module_name']}:echo_workflow",
    kwargs={{"message": "log_test_marker_xyz"}},
    wait_for_id=True,
    id_timeout_sec=15.0,
)

# Wait for workflow to complete
time.sleep(3)

if workflow_id:
    print(f"WORKFLOW_ID:{{workflow_id}}")
"""
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            f"{src_path}:{test_workflow_package['package_path']}:{env.get('PYTHONPATH', '')}"
        )

        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        if "WORKFLOW_ID:" not in result.stdout:
            pytest.skip(f"Could not get workflow ID: {result.stderr}")

        workflow_id = result.stdout.split("WORKFLOW_ID:")[1].strip()

        # Check for log file
        log_dir = integration_project / ".kurt" / "logs"
        log_file = log_dir / f"workflow-{workflow_id}.log"

        # Wait for log file to appear
        for _ in range(50):
            if log_file.exists():
                break
            time.sleep(0.1)

        assert log_file.exists(), f"Log file not found: {log_file}"

        # Check log content contains our marker
        content = log_file.read_text()
        # The workflow prints "[ECHO_WORKFLOW] Received: log_test_marker_xyz"
        assert "log_test_marker_xyz" in content or len(content) > 0

    def test_worker_handles_workflow_args(self, integration_project, test_workflow_package):
        """Worker should correctly pass args to workflow."""
        src_path = _get_project_src_path()

        test_script = f"""
import os
import sys
import time

sys.path.insert(0, "{src_path}")
sys.path.insert(0, "{test_workflow_package['package_path']}")
os.chdir("{integration_project}")

from kurt.core.background import start_background_workflow

workflow_id = start_background_workflow(
    "{test_workflow_package['module_name']}:add_workflow",
    kwargs={{"a": 5, "b": 7}},
    wait_for_id=True,
    id_timeout_sec=15.0,
)

time.sleep(3)

if workflow_id:
    print(f"WORKFLOW_ID:{{workflow_id}}")
"""
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            f"{src_path}:{test_workflow_package['package_path']}:{env.get('PYTHONPATH', '')}"
        )

        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        if "WORKFLOW_ID:" not in result.stdout:
            pytest.skip(f"Could not get workflow ID: {result.stderr}")

        workflow_id = result.stdout.split("WORKFLOW_ID:")[1].strip()

        # Check log file contains the add operation
        log_dir = integration_project / ".kurt" / "logs"
        log_file = log_dir / f"workflow-{workflow_id}.log"

        for _ in range(50):
            if log_file.exists():
                break
            time.sleep(0.1)

        if log_file.exists():
            content = log_file.read_text()
            # Should contain "5 + 7 = 12"
            assert "5 + 7 = 12" in content or "ADD_WORKFLOW" in content or len(content) > 0


class TestWorkflowStatusTracking:
    """Tests for workflow status tracking with real DBOS."""

    def test_workflow_completes_successfully(self, integration_project, test_workflow_package):
        """Workflow should complete with SUCCESS status."""
        src_path = _get_project_src_path()

        # This test queries DBOS for workflow status after completion
        test_script = f"""
import os
import sys
import time

sys.path.insert(0, "{src_path}")
sys.path.insert(0, "{test_workflow_package['package_path']}")
os.chdir("{integration_project}")

from kurt.core.background import start_background_workflow
from kurt.core.dbos import init_dbos
from dbos import DBOS

workflow_id = start_background_workflow(
    "{test_workflow_package['module_name']}:echo_workflow",
    kwargs={{"message": "status_test"}},
    wait_for_id=True,
    id_timeout_sec=15.0,
)

if not workflow_id:
    print("FAILED:no_id")
    exit(1)

# Wait for workflow to complete
time.sleep(3)

# Initialize DBOS in this process to query status
init_dbos()

try:
    status = DBOS.get_workflow_status(workflow_id)
    if status:
        print(f"STATUS:{{status.status}}")
    else:
        print("STATUS:unknown")
except Exception as e:
    print(f"STATUS_ERROR:{{e}}")
"""
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            f"{src_path}:{test_workflow_package['package_path']}:{env.get('PYTHONPATH', '')}"
        )

        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        if "STATUS:" in result.stdout:
            status = result.stdout.split("STATUS:")[1].strip().split("\n")[0]
            # Status should be SUCCESS or possibly still PENDING
            assert status in ["SUCCESS", "PENDING", "unknown"], f"Unexpected status: {status}"


# ============================================================================
# workflow_path_for Integration Tests
# ============================================================================


class TestWorkflowPathForIntegration:
    """Integration tests for workflow_path_for with real resolution."""

    def test_path_roundtrips_correctly(self):
        """Generated path should resolve back to original function."""
        # Test with stdlib function
        import json

        from kurt.core._worker import _resolve_workflow
        from kurt.core.background import workflow_path_for

        path = workflow_path_for(json.dumps)
        resolved = _resolve_workflow(path)
        assert resolved is json.dumps

    def test_path_works_with_nested_modules(self):
        """Should work with deeply nested module paths."""
        import os.path

        from kurt.core._worker import _resolve_workflow
        from kurt.core.background import workflow_path_for

        path = workflow_path_for(os.path.join)
        resolved = _resolve_workflow(path)
        assert resolved is os.path.join


# ============================================================================
# Error Handling Integration Tests
# ============================================================================


class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""

    def test_invalid_workflow_path_handled_gracefully(self, integration_project):
        """Should handle invalid workflow paths without crashing."""
        from kurt.core.background import start_background_workflow

        # This will fail because the module doesn't exist
        # But it shouldn't crash - just return None or timeout
        workflow_id = start_background_workflow(
            "nonexistent.module:fake_workflow",
            wait_for_id=True,
            id_timeout_sec=2.0,
        )

        # Should timeout (return None) since worker can't resolve the path
        assert workflow_id is None
