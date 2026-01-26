"""
Test fixtures for tool tests.

Provides fixtures for testing tools with SQLModel persistence.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


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

    # Create sources directory
    sources_dir = repo_path / "sources"
    sources_dir.mkdir()

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

    Now redirects to SQLModel-based persistence.
    """
    pytest.skip("Dolt persistence tests deprecated - use tmp_sqlmodel_project")


@pytest.fixture
def tool_context_with_sqlmodel(tmp_sqlmodel_project):
    """
    Create a ToolContext with SQLModel project for testing persistence.

    Use this fixture when testing tool execution with real database writes.
    """
    from kurt.tools.base import ToolContext

    repo_path = tmp_sqlmodel_project
    return ToolContext(
        settings={"project_root": str(repo_path)},
    )


@pytest.fixture
def tool_context_with_dolt(tmp_dolt_project):
    """
    DEPRECATED: Use tool_context_with_sqlmodel instead.
    """
    pytest.skip("Dolt context deprecated - use tool_context_with_sqlmodel")
