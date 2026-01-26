"""
Test fixtures for map workflow tests.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_markdown_folder(tmp_path: Path) -> Path:
    """
    Create a temporary folder with markdown files for testing.
    """
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    # Create some markdown files
    (docs_dir / "intro.md").write_text("# Introduction\n\nThis is the intro.")
    (docs_dir / "guide.md").write_text("# User Guide\n\nHow to use this.")
    (docs_dir / "api.mdx").write_text("# API Reference\n\nAPI docs here.")

    # Create a subdirectory with more files
    nested = docs_dir / "advanced"
    nested.mkdir()
    (nested / "config.md").write_text("# Configuration\n\nAdvanced config.")
    (nested / "plugins.md").write_text("# Plugins\n\nPlugin system.")

    # Create a hidden directory that should be ignored
    hidden = docs_dir / ".hidden"
    hidden.mkdir()
    (hidden / "secret.md").write_text("# Secret\n\nHidden file.")

    return docs_dir


@pytest.fixture
def tmp_project_dir(tmp_path: Path, monkeypatch) -> Path:
    """
    Create a temporary project directory with .kurt structure.
    """
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.delenv("DATABASE_URL", raising=False)

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    yield tmp_path

    os.chdir(original_cwd)


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
