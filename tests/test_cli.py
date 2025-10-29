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


def test_all_commands_registered(runner):
    """Test that all commands are properly registered and have Click decorators.

    This smoke test catches issues where commands are imported but not decorated
    with @click.command() or @click.group(), which causes AttributeError at startup.
    """
    # Test main command help works
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, f"Main help failed: {result.output}"

    # Test that all expected top-level commands are registered
    expected_commands = ["init", "cms", "content", "migrate", "project", "research", "status"]
    for cmd in expected_commands:
        assert cmd in result.output, f"Command '{cmd}' not found in main help"

    # Test each command group's help to ensure they're properly decorated
    command_groups = {
        "cms": ["search", "fetch", "types", "onboard", "import", "publish"],
        "content": ["add", "list", "stats", "cluster", "fetch"],
        "migrate": ["status", "apply"],
        "project": ["status"],
        "research": [],  # research might not have subcommands
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
    """Test that 'project status' command is properly registered."""
    result = runner.invoke(main, ["project", "status", "--help"])
    assert result.exit_code == 0, f"'project status' help failed: {result.output}"
    assert "status" in result.output.lower()
