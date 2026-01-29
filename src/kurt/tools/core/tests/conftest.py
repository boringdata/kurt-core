"""
Test fixtures for tool tests.

Provides fixtures for testing tools with database persistence.
Uses Dolt-based fixtures from kurt.conftest (discovered automatically by pytest).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def tmp_sqlmodel_project(tmp_project):
    """
    Create a temporary project with SQLModel tables for tool persistence tests.

    This fixture now uses Dolt (not SQLite) since SQLite support was removed.
    It wraps the tmp_project fixture from kurt.conftest.

    Sets up:
    - Temp directory with .dolt database
    - kurt.config file
    - Dolt SQL server on a unique port
    - map_documents and fetch_documents tables

    Yields:
        Path: The temp project path
    """
    # tmp_project already sets up everything needed
    yield tmp_project


@pytest.fixture
def tmp_dolt_project(tmp_project):
    """
    Alias for tmp_project.

    Use tmp_sqlmodel_project or tmp_project instead.
    """
    yield tmp_project


@pytest.fixture
def tool_context_with_sqlmodel(tmp_sqlmodel_project):
    """
    Create a ToolContext with database project for testing persistence.

    Use this fixture when testing tool execution with real database writes.
    """
    from kurt.tools.core.base import ToolContext

    repo_path = tmp_sqlmodel_project
    return ToolContext(
        settings={"project_root": str(repo_path)},
    )


@pytest.fixture
def tool_context_with_dolt(tmp_dolt_project):
    """
    Alias for tool_context_with_sqlmodel.
    """
    from kurt.tools.core.base import ToolContext

    repo_path = tmp_dolt_project
    return ToolContext(
        settings={"project_root": str(repo_path)},
    )
