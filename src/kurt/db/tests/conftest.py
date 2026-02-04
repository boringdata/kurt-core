"""Pytest fixtures for DoltDB tests.

Provides fixtures for:
- dolt_available: Check if dolt CLI is installed
- tmp_dolt_repo: Create a temporary Dolt repository
- dolt_server: Start a dolt sql-server for integration tests
- server_db: DoltDB instance connected to the test server
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Generator

import pytest

from kurt.db.dolt import DoltDB


def _find_free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def _wait_for_server(host: str, port: int, timeout: float = 10.0) -> bool:
    """Wait for server to accept connections.

    Args:
        host: Server host
        port: Server port
        timeout: Maximum time to wait in seconds

    Returns:
        True if server is ready, False if timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect((host, port))
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.1)
    return False


@pytest.fixture
def dolt_available() -> bool:
    """Check if dolt CLI is available."""
    return shutil.which("dolt") is not None


@pytest.fixture
def tmp_dolt_repo(tmp_path: Path, dolt_available: bool) -> Path | None:
    """Create a temporary Dolt repository for testing.

    Returns None if dolt is not installed.
    """
    if not dolt_available:
        pytest.skip("Dolt CLI not installed")

    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize dolt repo
    subprocess.run(
        ["dolt", "init"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Configure git user for commits (--set required in newer Dolt versions)
    subprocess.run(
        ["dolt", "config", "--local", "--set", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["dolt", "config", "--local", "--set", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def dolt_server(tmp_dolt_repo: Path) -> Generator[tuple[Path, int], None, None]:
    """Start a dolt sql-server for testing.

    Yields:
        Tuple of (repo_path, port) for the running server
    """
    port = _find_free_port()

    # Start dolt sql-server
    # Note: --user and --password flags removed in newer Dolt versions
    # Server starts with root user by default
    proc = subprocess.Popen(
        [
            "dolt", "sql-server",
            "--host", "localhost",
            "--port", str(port),
        ],
        cwd=tmp_dolt_repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for server to be ready
        if not _wait_for_server("localhost", port, timeout=10.0):
            proc.terminate()
            proc.wait(timeout=5)
            stdout, stderr = proc.communicate(timeout=5)
            pytest.fail(
                f"Dolt server failed to start on port {port}.\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )

        yield tmp_dolt_repo, port

    finally:
        # Stop the server
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


@pytest.fixture
def server_db(dolt_server: tuple[Path, int]) -> Generator[DoltDB, None, None]:
    """Create a DoltDB instance connected to the test server.

    Yields:
        DoltDB instance configured for the test server
    """
    repo_path, port = dolt_server

    db = DoltDB(
        path=repo_path,
        mode="server",
        host="localhost",
        port=port,
        user="root",
        password="",
        database=repo_path.name,
    )

    try:
        yield db
    finally:
        db.close()
