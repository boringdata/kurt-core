"""Tests for init CLI command."""

from __future__ import annotations

import json
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


class TestInitIdeSetup:
    """Tests for IDE-specific setup (agents, hooks, symlinks)."""

    def test_init_creates_agents_directory(self, cli_runner_sqlite):
        """Test init creates .agents directory with AGENTS.md."""
        result = cli_runner_sqlite.invoke(init, [])
        assert_cli_success(result)

        agents_dir = Path(".agents")
        agents_md = agents_dir / "AGENTS.md"

        assert agents_dir.exists(), ".agents directory should be created"
        assert agents_md.exists(), ".agents/AGENTS.md should be created"

    def test_init_creates_claude_symlink(self, cli_runner_sqlite):
        """Test init creates .claude/CLAUDE.md symlink to .agents/AGENTS.md."""
        result = cli_runner_sqlite.invoke(init, ["--ide", "claude"])
        assert_cli_success(result)

        claude_md = Path(".claude/CLAUDE.md")
        assert claude_md.exists() or claude_md.is_symlink(), ".claude/CLAUDE.md should exist"

        if claude_md.is_symlink():
            target = claude_md.resolve()
            assert target.name == "AGENTS.md", "Symlink should point to AGENTS.md"

    def test_init_creates_claude_instructions_symlink(self, cli_runner_sqlite):
        """Test init creates .claude/instructions/AGENTS.md symlink."""
        result = cli_runner_sqlite.invoke(init, ["--ide", "claude"])
        assert_cli_success(result)

        instructions_md = Path(".claude/instructions/AGENTS.md")
        assert (
            instructions_md.exists() or instructions_md.is_symlink()
        ), ".claude/instructions/AGENTS.md should exist"

    def test_init_creates_claude_settings_with_hooks(self, cli_runner_sqlite):
        """Test init creates .claude/settings.json with hooks configured."""
        result = cli_runner_sqlite.invoke(init, ["--ide", "claude"])
        assert_cli_success(result)

        settings_file = Path(".claude/settings.json")
        assert settings_file.exists(), ".claude/settings.json should be created"

        with open(settings_file) as f:
            settings = json.load(f)

        assert "hooks" in settings, "settings.json should contain hooks"
        hooks = settings["hooks"]

        # Check for expected hook types
        assert "SessionStart" in hooks, "SessionStart hook should be configured"
        assert "PreToolUse" in hooks, "PreToolUse hook should be configured"
        assert "PostToolUse" in hooks, "PostToolUse hook should be configured"

    def test_init_claude_hooks_have_correct_structure(self, cli_runner_sqlite):
        """Test Claude hooks have the expected structure."""
        result = cli_runner_sqlite.invoke(init, ["--ide", "claude"])
        assert_cli_success(result)

        settings_file = Path(".claude/settings.json")
        with open(settings_file) as f:
            settings = json.load(f)

        # Check SessionStart hook structure
        session_start = settings["hooks"]["SessionStart"]
        assert isinstance(session_start, list), "SessionStart should be a list"
        assert len(session_start) > 0, "SessionStart should have at least one entry"
        assert "hooks" in session_start[0], "Hook entry should have 'hooks' key"

        # Check that hooks contain kurt status command
        hook_commands = []
        for entry in session_start:
            for hook in entry.get("hooks", []):
                if hook.get("type") == "command":
                    hook_commands.append(hook.get("command", ""))

        assert any(
            "kurt status" in cmd for cmd in hook_commands
        ), "SessionStart should include 'kurt status' command"

    def test_init_creates_cursor_symlink(self, cli_runner_sqlite):
        """Test init creates .cursor/rules/KURT.mdc symlink."""
        result = cli_runner_sqlite.invoke(init, ["--ide", "cursor"])
        assert_cli_success(result)

        cursor_rule = Path(".cursor/rules/KURT.mdc")
        assert (
            cursor_rule.exists() or cursor_rule.is_symlink()
        ), ".cursor/rules/KURT.mdc should exist"

        if cursor_rule.is_symlink():
            target = cursor_rule.resolve()
            assert target.name == "AGENTS.md", "Symlink should point to AGENTS.md"

    def test_init_both_ides_creates_all_files(self, cli_runner_sqlite):
        """Test init --ide both creates both Claude and Cursor configurations."""
        result = cli_runner_sqlite.invoke(init, ["--ide", "both"])
        assert_cli_success(result)

        # Check Claude files
        assert Path(".claude/CLAUDE.md").exists() or Path(".claude/CLAUDE.md").is_symlink()
        assert Path(".claude/settings.json").exists()

        # Check Cursor files
        assert (
            Path(".cursor/rules/KURT.mdc").exists() or Path(".cursor/rules/KURT.mdc").is_symlink()
        )

    def test_init_preserves_existing_settings(self, cli_runner_sqlite):
        """Test init merges hooks into existing settings.json without overwriting."""
        # Create existing settings with custom key
        claude_dir = Path(".claude")
        claude_dir.mkdir(parents=True, exist_ok=True)
        existing_settings = {"customKey": "customValue", "hooks": {"CustomHook": []}}
        with open(claude_dir / "settings.json", "w") as f:
            json.dump(existing_settings, f)

        result = cli_runner_sqlite.invoke(init, ["--ide", "claude"])
        assert_cli_success(result)

        with open(claude_dir / "settings.json") as f:
            settings = json.load(f)

        # Custom key should be preserved
        assert settings.get("customKey") == "customValue", "Existing keys should be preserved"
        # Kurt hooks should be added
        assert "SessionStart" in settings["hooks"], "Kurt hooks should be added"
