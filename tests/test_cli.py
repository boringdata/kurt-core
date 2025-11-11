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


def test_init_command(tmp_path, monkeypatch):
    """Test init command in isolated temp project."""
    from click.testing import CliRunner

    # Create a completely fresh temp directory (no config, no migrations)
    project_dir = tmp_path / "fresh-project"
    project_dir.mkdir()

    # Change to temp project directory
    monkeypatch.chdir(project_dir)
    monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

    runner = CliRunner()
    result = runner.invoke(main, ["init"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert "Initializing Kurt project" in result.output

    # Check that config was created
    config_file = project_dir / "kurt.config"
    assert config_file.exists()


def test_all_commands_registered(runner):
    """Test that all commands are properly registered and have Click decorators.

    This smoke test catches issues where commands are imported but not decorated
    with @click.command() or @click.group(), which causes AttributeError at startup.
    """
    # Test main command help works
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, f"Main help failed: {result.output}"

    # Test that all expected top-level commands are registered
    expected_commands = [
        "init",
        "admin",
        "content",
        "integrations",
        "status",
        "workflows",
    ]
    for cmd in expected_commands:
        assert cmd in result.output, f"Command '{cmd}' not found in main help"

    # Test each command group's help to ensure they're properly decorated
    command_groups = {
        "content": [
            "fetch",
            "map",
            "cluster",
            "list",
            "get",
            "index",
            "delete",
            "stats",
            "list-clusters",
            "sync-metadata",
        ],
        "integrations": ["analytics", "cms", "research"],
        "admin": ["feedback", "migrate", "telemetry", "project"],
    }

    for group, subcommands in command_groups.items():
        result = runner.invoke(main, [group, "--help"])
        assert result.exit_code == 0, f"Command group '{group}' failed: {result.output}"

        for subcmd in subcommands:
            assert subcmd in result.output, f"Subcommand '{group} {subcmd}' not found in help"

    # Test standalone commands
    standalone_commands = ["status"]
    for cmd in standalone_commands:
        result = runner.invoke(main, [cmd, "--help"])
        assert result.exit_code == 0, f"Command '{cmd}' help failed: {result.output}"


def test_content_stats_help(runner):
    """Test that 'content stats' command is properly registered."""
    result = runner.invoke(main, ["content", "stats", "--help"])
    assert result.exit_code == 0, f"'content stats' help failed: {result.output}"
    assert "Show content statistics" in result.output or "statistics" in result.output.lower()


def test_status_help(runner):
    """Test that 'status' command is properly registered."""
    result = runner.invoke(main, ["status", "--help"])
    assert result.exit_code == 0, f"'status' help failed: {result.output}"
    assert "status" in result.output.lower()


def test_project_status_help(runner):
    """Test that 'admin project status' command is properly registered."""
    result = runner.invoke(main, ["admin", "project", "status", "--help"])
    assert result.exit_code == 0, f"'admin project status' help failed: {result.output}"
    assert "status" in result.output.lower()
