"""
Test fixtures for tool tests.

Provides fixtures for testing tools with real Dolt persistence.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dolt_project(tmp_path: Path, monkeypatch):
    """
    Create a temporary project with DoltDB initialized for tool tests.

    This fixture sets up a real Dolt database with the required schema tables
    (document_registry, map_results, fetch_results) so tools can test
    actual persistence without dry_run=True.

    Sets up:
    - Temp directory with initialized Dolt repo
    - Schema tables for map/fetch persistence
    - Changes cwd to temp directory

    Yields:
        tuple[Path, DoltDB]: The temp path and DoltDB instance
    """
    # Skip if dolt not installed
    if not shutil.which("dolt"):
        pytest.skip("Dolt CLI not installed")

    from kurt.db.dolt import DoltDB

    # Create project structure
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    # Initialize dolt repo using CLI directly
    subprocess.run(
        ["dolt", "init"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Set up environment
    original_cwd = os.getcwd()
    os.chdir(repo_path)

    # Create DoltDB instance
    db = DoltDB(repo_path)

    # Create schema tables required for tool persistence
    # document_registry: Central registry of all known documents
    db.execute("""
        CREATE TABLE IF NOT EXISTS document_registry (
            document_id VARCHAR(12) PRIMARY KEY,
            url VARCHAR(2048) NOT NULL,
            url_hash VARCHAR(64) NOT NULL,
            source_type VARCHAR(20) NOT NULL,
            first_seen_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
            UNIQUE KEY idx_registry_url_hash (url_hash),
            INDEX idx_registry_url (url(255))
        )
    """)

    # map_results: Output from MapTool
    db.execute("""
        CREATE TABLE IF NOT EXISTS map_results (
            document_id VARCHAR(12) NOT NULL,
            run_id VARCHAR(36) NOT NULL,
            url TEXT NOT NULL,
            source_type VARCHAR(20) DEFAULT 'url',
            discovery_method VARCHAR(50) NOT NULL,
            discovery_url TEXT,
            title TEXT,
            status VARCHAR(20) DEFAULT 'success',
            error TEXT,
            metadata JSON,
            created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (document_id, run_id),
            INDEX idx_map_created (created_at),
            INDEX idx_map_status (status)
        )
    """)

    # fetch_results: Output from FetchTool
    db.execute("""
        CREATE TABLE IF NOT EXISTS fetch_results (
            document_id VARCHAR(12) NOT NULL,
            run_id VARCHAR(36) NOT NULL,
            url TEXT NOT NULL,
            status VARCHAR(20) NOT NULL,
            content_path TEXT,
            content_hash VARCHAR(64),
            content_length INT,
            fetch_engine VARCHAR(50),
            error TEXT,
            metadata JSON,
            created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (document_id, run_id),
            INDEX idx_fetch_created (created_at),
            INDEX idx_fetch_status (status)
        )
    """)

    yield repo_path, db

    os.chdir(original_cwd)


@pytest.fixture
def tool_context_with_dolt(tmp_dolt_project):
    """
    Create a ToolContext with a real Dolt project for testing persistence.

    Use this fixture when testing tool execution with real database writes.
    """
    from kurt.tools.base import ToolContext

    repo_path, db = tmp_dolt_project
    return ToolContext(
        settings={"project_root": str(repo_path)},
    )
