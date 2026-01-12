"""Tests for init CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.cli.init import init
from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestInitCommand:
    """Tests for `kurt init` command."""

    def test_init_help(self, cli_runner: CliRunner):
        """Test init command shows help."""
        result = invoke_cli(cli_runner, init, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Initialize a new Kurt project")

    def test_init_shows_options(self, cli_runner: CliRunner):
        """Test init command lists options in help."""
        result = invoke_cli(cli_runner, init, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--db-path")
        assert_output_contains(result, "--sources-path")
        assert_output_contains(result, "--projects-path")
        assert_output_contains(result, "--rules-path")
        assert_output_contains(result, "--ide")

    def test_init_ide_choices(self, cli_runner: CliRunner):
        """Test init --ide accepts valid choices."""
        result = invoke_cli(cli_runner, init, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "claude")
        assert_output_contains(result, "cursor")
        assert_output_contains(result, "both")


@pytest.fixture
def cli_runner_sqlite(cli_runner: CliRunner, monkeypatch):
    """CLI runner with isolated filesystem and SQLite database."""
    # Remove DATABASE_URL to force SQLite
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with cli_runner.isolated_filesystem():
        yield cli_runner


class TestInitFunctional:
    """Functional tests for `kurt init` command using SQLite."""

    def test_init_creates_config_file(self, cli_runner_sqlite):
        """Test init command creates config file.

        This test catches bugs where init fails to create configuration files.
        """
        result = cli_runner_sqlite.invoke(init, [])
        assert_cli_success(result)
        assert_output_contains(result, "Created config")
        assert Path("kurt.config").exists()

    def test_init_creates_database(self, cli_runner_sqlite):
        """Test init command creates database."""
        result = cli_runner_sqlite.invoke(init, [])
        assert_cli_success(result)
        assert Path(".kurt/kurt.sqlite").exists()

    def test_init_creates_env_example(self, cli_runner_sqlite):
        """Test init command creates .env.example file."""
        result = cli_runner_sqlite.invoke(init, [])
        assert_cli_success(result)
        assert_output_contains(result, ".env.example")
        assert Path(".env.example").exists()

    def test_init_custom_db_path(self, cli_runner_sqlite):
        """Test init command respects --db-path option.

        This test catches bugs where options are not passed correctly.
        """
        result = cli_runner_sqlite.invoke(init, ["--db-path", "custom/data.db"])
        assert_cli_success(result)
        assert_output_contains(result, "custom/data.db")

    def test_init_custom_sources_path(self, cli_runner_sqlite):
        """Test init command respects --sources-path option."""
        result = cli_runner_sqlite.invoke(init, ["--sources-path", "my_sources"])
        assert_cli_success(result)
        assert_output_contains(result, "my_sources")

    def test_init_custom_projects_path(self, cli_runner_sqlite):
        """Test init command respects --projects-path option."""
        result = cli_runner_sqlite.invoke(init, ["--projects-path", "my_projects"])
        assert_cli_success(result)
        assert_output_contains(result, "my_projects")

    def test_init_custom_rules_path(self, cli_runner_sqlite):
        """Test init command respects --rules-path option."""
        result = cli_runner_sqlite.invoke(init, ["--rules-path", "my_rules"])
        assert_cli_success(result)
        assert_output_contains(result, "my_rules")

    def test_init_config_has_correct_values(self, cli_runner_sqlite):
        """Test init command writes correct values to config."""
        result = cli_runner_sqlite.invoke(
            init,
            [
                "--db-path",
                "test.db",
                "--sources-path",
                "src_content",
                "--projects-path",
                "proj",
                "--rules-path",
                "r",
            ],
        )
        assert_cli_success(result)

        # Read and verify config
        from kurt.config import load_config

        config = load_config()
        assert config.PATH_DB == "test.db"
        assert config.PATH_SOURCES == "src_content"
        assert config.PATH_PROJECTS == "proj"
        assert config.PATH_RULES == "r"

    def test_init_ide_claude_only(self, cli_runner_sqlite):
        """Test init command with --ide claude.

        The command should succeed even if AGENTS.md isn't found in package.
        """
        result = cli_runner_sqlite.invoke(init, ["--ide", "claude"])
        assert_cli_success(result)
        # Should mention Claude Code setup (either success or warning)
        assert "Claude Code" in result.output or "claude" in result.output.lower()

    def test_init_ide_cursor_only(self, cli_runner_sqlite):
        """Test init command with --ide cursor.

        The command should succeed even if AGENTS.md isn't found in package.
        """
        result = cli_runner_sqlite.invoke(init, ["--ide", "cursor"])
        assert_cli_success(result)
        # Should mention Cursor setup (either success or warning)
        assert "Cursor" in result.output or "cursor" in result.output.lower()


class TestInitIdempotency:
    """Tests for init command idempotency behavior."""

    def test_init_detects_existing_project(self, cli_runner_sqlite):
        """Test init detects when project already exists."""
        # First init
        result = cli_runner_sqlite.invoke(init, [])
        assert_cli_success(result)

        # Second init should warn
        result = cli_runner_sqlite.invoke(init, [], input="n\n")
        assert_cli_success(result)
        assert_output_contains(result, "already initialized")
