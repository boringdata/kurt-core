"""
Test fixtures for fetch tool tests.

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

    Yields:
        Path: The temp project path
    """
    yield tmp_project


@pytest.fixture
def tmp_dolt_project(tmp_project):
    """Alias for tmp_project."""
    yield tmp_project


@pytest.fixture
def tool_context_with_sqlmodel(tmp_sqlmodel_project):
    """
    Create a ToolContext with database project for testing persistence.
    """
    from kurt.tools.core.base import ToolContext

    repo_path = tmp_sqlmodel_project
    return ToolContext(
        settings={"project_root": str(repo_path)},
    )


@pytest.fixture
def tool_context_with_dolt(tmp_dolt_project):
    """Alias for tool_context_with_sqlmodel."""
    from kurt.tools.core.base import ToolContext

    repo_path = tmp_dolt_project
    return ToolContext(
        settings={"project_root": str(repo_path)},
    )
