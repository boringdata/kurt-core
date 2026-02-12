"""
Root pytest configuration for kurt.

Provides test fixtures for CLI testing, database testing, and sample data.
"""

from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

# Re-export fixtures from documents tests
from kurt.documents.tests.conftest import (
    tmp_project,
    tmp_project_with_docs,
)


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    """Wait for a port to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.1)
    return False

# ============================================================================
# CLI Testing Fixtures
# ============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def cli_runner_isolated(cli_runner: CliRunner):
    """Create a Click CLI runner with isolated filesystem."""
    with cli_runner.isolated_filesystem():
        yield cli_runner


def invoke_cli(runner: CliRunner, cmd, args: list[str], **kwargs):
    """
    Helper to invoke CLI command.

    Args:
        runner: Click test runner
        cmd: Click command or group
        args: Command arguments
        **kwargs: Additional arguments to runner.invoke()

    Returns:
        Click Result object
    """
    return runner.invoke(cmd, args, catch_exceptions=False, **kwargs)


def assert_cli_success(result, msg: str = None):
    """Assert CLI command succeeded (exit code 0)."""
    if result.exit_code != 0:
        error_msg = f"CLI failed (exit code {result.exit_code})"
        if msg:
            error_msg = f"{msg}: {error_msg}"
        if result.output:
            error_msg += f"\nOutput: {result.output}"
        raise AssertionError(error_msg)


def assert_cli_failure(result, expected_code: int = None, msg: str = None):
    """Assert CLI command failed."""
    if result.exit_code == 0:
        error_msg = "CLI succeeded but expected failure"
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)

    if expected_code is not None and result.exit_code != expected_code:
        raise AssertionError(f"Expected exit code {expected_code}, got {result.exit_code}")


def assert_output_contains(result, text: str):
    """Assert CLI output contains text."""
    if text not in result.output:
        raise AssertionError(f"Expected output to contain '{text}'\nGot: {result.output}")


def assert_json_output(result) -> dict:
    """Assert CLI output is valid JSON and return it."""
    import json

    try:
        return json.loads(result.output)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Expected JSON output, got:\n{result.output}") from e


# ============================================================================
# Database Testing Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def tmp_database(tmp_path_factory):
    """
    Fixture for a temporary Dolt database with its own server.

    Creates ONE shared Dolt database for the entire session.
    Sets DATABASE_URL environment variable.

    Using session scope dramatically speeds up tests by avoiding
    repeated server startup/shutdown. All tests share one server.
    """
    # Skip if dolt is not installed
    if not shutil.which("dolt"):
        pytest.skip("Dolt CLI not installed")

    # Create temp directory for this session
    tmp_path = tmp_path_factory.mktemp("dolt_session")

    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Initialize dolt repo
    env = os.environ.copy()
    env["DOLT_DISABLE_ACCOUNT_REGISTRATION"] = "true"
    subprocess.run(["dolt", "init"], cwd=tmp_path, capture_output=True, env=env)

    # Find a free port for this test's Dolt server
    port = _find_free_port()

    # Start dolt sql-server on the unique port
    server_process = subprocess.Popen(
        ["dolt", "sql-server", "--port", str(port), "--host", "127.0.0.1"],
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )

    # Wait for server to be ready
    if not _wait_for_port(port, timeout=10.0):
        server_process.terminate()
        os.chdir(original_cwd)
        pytest.fail(f"Dolt server failed to start on port {port}")

    # Set DATABASE_URL to connect to this session's Dolt server
    # Database name is the directory name (created by dolt init)
    database_name = tmp_path.name
    database_url = f"mysql+pymysql://root@127.0.0.1:{port}/{database_name}"
    os.environ["DATABASE_URL"] = database_url

    # Initialize the database
    from kurt.db import init_database

    init_database()

    yield tmp_path

    # Cleanup: stop the Dolt server
    try:
        os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        server_process.wait(timeout=5)
    except Exception:
        try:
            server_process.kill()
        except Exception:
            pass

    os.chdir(original_cwd)
    # Restore original DATABASE_URL if it existed
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def tmp_database_with_data(tmp_database: Path):
    """
    Fixture with a temporary database pre-populated with sample data.

    Use when tests need existing data. Session-scoped for performance.
    """
    from sqlalchemy import text

    from kurt.db import managed_session

    with managed_session() as session:
        # Create a sample table (use VARCHAR for MySQL/Dolt compatibility)
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS test_documents (
                id VARCHAR(255) PRIMARY KEY,
                url VARCHAR(512) NOT NULL,
                title VARCHAR(255),
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )

        # Insert sample data
        session.execute(
            text("""
            INSERT INTO test_documents (id, url, title, content)
            VALUES
                ('doc-1', 'https://example.com/1', 'Test Doc 1', 'Content 1'),
                ('doc-2', 'https://example.com/2', 'Test Doc 2', 'Content 2'),
                ('doc-3', 'https://example.com/3', 'Test Doc 3', 'Content 3')
        """)
        )
        session.commit()

    yield tmp_database


# ============================================================================
# Recording Hooks for Testing
# ============================================================================


class RecordingHooks:
    """
    Step hooks that record all calls for testing.

    Usage:
        hooks = RecordingHooks()
        # ... run step with hooks ...
        assert hooks.on_start_calls == 1
        assert hooks.on_row_success_calls > 0
    """

    def __init__(self):
        self.on_start_calls = 0
        self.on_row_success_calls = 0
        self.on_row_error_calls = 0
        self.on_result_calls = 0
        self.on_end_calls = 0

        self.start_events: list[dict[str, Any]] = []
        self.row_success_events: list[dict[str, Any]] = []
        self.row_error_events: list[dict[str, Any]] = []
        self.result_events: list[dict[str, Any]] = []
        self.end_events: list[dict[str, Any]] = []

    def on_start(self, **kwargs):
        self.on_start_calls += 1
        self.start_events.append(kwargs)

    def on_row_success(self, **kwargs):
        self.on_row_success_calls += 1
        self.row_success_events.append(kwargs)

    def on_row_error(self, **kwargs):
        self.on_row_error_calls += 1
        self.row_error_events.append(kwargs)

    def on_result(self, **kwargs):
        self.on_result_calls += 1
        self.result_events.append(kwargs)

    def on_end(self, **kwargs):
        self.on_end_calls += 1
        self.end_events.append(kwargs)


@pytest.fixture
def recording_hooks():
    """Fixture that provides RecordingHooks for testing step lifecycle."""
    return RecordingHooks()


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    import pandas as pd

    return pd.DataFrame({
        "id": [1, 2, 3],
        "content": ["Hello world", "Test content", "Sample text"],
        "category": ["A", "B", "A"],
    })


@pytest.fixture
def large_df():
    """Create a larger DataFrame for batch testing."""
    import pandas as pd

    return pd.DataFrame({
        "id": list(range(100)),
        "content": [f"Content item {i}" for i in range(100)],
        "value": [i * 1.5 for i in range(100)],
    })


__all__ = [
    # CLI fixtures
    "cli_runner",
    "cli_runner_isolated",
    "invoke_cli",
    "assert_cli_success",
    "assert_cli_failure",
    "assert_output_contains",
    "assert_json_output",
    # Database fixtures
    "tmp_database",
    "tmp_database_with_data",
    # Hooks
    "RecordingHooks",
    "recording_hooks",
    # Sample data
    "sample_df",
    "large_df",
    # Re-exported from documents
    "tmp_project",
    "tmp_project_with_docs",
]
