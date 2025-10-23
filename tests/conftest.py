"""
Shared test fixtures for Kurt tests.

Provides isolated temporary project setup for running tests.
"""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(monkeypatch, tmp_path):
    """
    Create isolated temporary Kurt project for testing.

    This fixture:
    - Creates a temp directory for the project
    - Changes working directory to temp project
    - Creates kurt.config file
    - Creates sources/ directory
    - Cleans up after test

    Usage:
        def test_something(tmp_project):
            # Test runs in isolated temp project
            # kurt.config exists
            # sources/ directory exists
            # Can run CLI commands without affecting real project
    """
    # Create temp project structure
    project_dir = tmp_path / "test-kurt-project"
    project_dir.mkdir()

    sources_dir = project_dir / "sources"
    sources_dir.mkdir()

    # Create kurt.config
    config_file = project_dir / "kurt.config"
    config_content = f"""# Kurt Configuration
# Auto-generated for testing

# Source content storage path (relative to project root)
SOURCE_PATH = "sources"

# Database connection (SQLite for testing)
DATABASE_URL = "sqlite:///{project_dir / '.kurt' / 'kurt.db'}"
"""
    config_file.write_text(config_content)

    # Create .kurt directory for database
    kurt_dir = project_dir / ".kurt"
    kurt_dir.mkdir()

    # Change to temp project directory
    monkeypatch.chdir(project_dir)

    # Set environment variable so Kurt finds this config
    monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

    yield project_dir

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def isolated_cli_runner(tmp_project):
    """
    Click CLI runner with isolated temp project.

    This fixture combines tmp_project with Click's CliRunner
    for testing CLI commands in isolation.

    Usage:
        def test_init_command(isolated_cli_runner):
            runner, project_dir = isolated_cli_runner
            result = runner.invoke(main, ['init'])
            assert result.exit_code == 0
    """
    from click.testing import CliRunner

    runner = CliRunner(
        env={"KURT_PROJECT_ROOT": str(tmp_project)}  # Ensure Kurt uses temp project
    )

    return runner, tmp_project
