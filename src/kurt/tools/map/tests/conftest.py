"""
Test fixtures for map workflow tests.
"""

from __future__ import annotations

import os
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
def tmp_sqlmodel_project(tmp_path: Path, monkeypatch):
    """
    Create a temporary project with SQLModel tables for tool persistence tests.

    Sets up:
    - Temp directory with .kurt structure
    - kurt.config file
    - SQLite database with map_documents and fetch_documents tables
    - Changes cwd to temp directory

    Yields:
        Path: The temp project path
    """
    from kurt.config import create_config
    from kurt.db import init_database, managed_session
    from kurt.db.database import ensure_tables
    from kurt.tools.fetch.models import FetchDocument
    from kurt.tools.map.models import MapDocument

    # Create project structure
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    kurt_dir = repo_path / ".kurt"
    kurt_dir.mkdir()

    # Set up environment
    monkeypatch.delenv("DATABASE_URL", raising=False)
    original_cwd = os.getcwd()
    os.chdir(repo_path)

    # Create config file
    create_config()

    # Initialize database and create tables
    init_database()
    with managed_session() as session:
        ensure_tables([MapDocument, FetchDocument], session=session)

    yield repo_path

    os.chdir(original_cwd)


@pytest.fixture
def tmp_dolt_project(tmp_path: Path, monkeypatch):
    """
    DEPRECATED: Use tmp_sqlmodel_project instead.

    Create a temporary project with DoltDB initialized for tool tests.
    Now redirects to SQLModel-based persistence.
    """
    # Skip if dolt not installed - but actually we don't need Dolt anymore
    # Just use SQLModel
    pytest.skip("Dolt persistence tests deprecated - use tmp_sqlmodel_project")
