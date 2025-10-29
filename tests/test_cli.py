"""Tests for Kurt CLI."""

import pytest
from click.testing import CliRunner

from kurt.cli import main


@pytest.fixture
def runner():
    """Create CLI runner (for simple tests without project isolation)."""
    return CliRunner()


def test_cli_version(runner):
    """Test --version flag."""
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "kurt" in result.output.lower()


def test_cli_help(runner):
    """Test --help flag."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Document intelligence CLI tool" in result.output


def test_init_command(isolated_cli_runner):
    """Test init command in isolated temp project."""
    runner, project_dir = isolated_cli_runner

    # Remove the config file created by tmp_project fixture
    # so we can test init creating it
    config_file = project_dir / "kurt.config"
    if config_file.exists():
        config_file.unlink()

    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert "Initializing Kurt project" in result.output
    assert config_file.exists()


@pytest.mark.skip(reason="Requires database setup - integration test")
def test_document_list(isolated_cli_runner):
    """Test document list command in isolated temp project."""
    runner, project_dir = isolated_cli_runner
    result = runner.invoke(main, ["document", "list"])
    # Command should run without error (may return empty list)
    assert result.exit_code == 0


@pytest.mark.skip(reason="Requires database setup - integration test")
def test_workspace_list(isolated_cli_runner):
    """Test workspace list command in isolated temp project."""
    runner, project_dir = isolated_cli_runner
    result = runner.invoke(main, ["workspace", "list"])
    # Command should run without error (may return empty list)
    assert result.exit_code == 0
