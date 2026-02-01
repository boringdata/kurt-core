"""
Test fixtures for map workflow tests.

Uses Dolt-based fixtures from kurt.conftest (discovered automatically by pytest).
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
