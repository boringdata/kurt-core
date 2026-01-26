"""Tests for main CLI and backwards compatibility aliases."""

import pytest
from click.testing import CliRunner

from kurt.cli.main import main


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestMainHelp:
    """Test main CLI help."""

    def test_main_help(self, cli_runner):
        """Test main help displays."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Kurt - Document intelligence CLI tool" in result.output

    def test_main_lists_commands(self, cli_runner):
        """Test main lists all expected commands."""
        result = cli_runner.invoke(main, ["--help"])
        expected = ["admin", "cloud", "connect", "docs", "doctor", "help",
                    "init", "repair", "serve", "status", "tool", "workflow"]
        for cmd in expected:
            assert cmd in result.output

    def test_deprecated_aliases_hidden(self, cli_runner):
        """Test deprecated aliases don't appear in help."""
        result = cli_runner.invoke(main, ["--help"])
        # These should NOT appear in the command list
        deprecated = ["agents", "content", "show", "sync"]
        # Split output into lines and check command section
        lines = result.output.split("\n")
        command_section = False
        for line in lines:
            if "Commands:" in line:
                command_section = True
                continue
            if command_section and line.strip():
                # Check that deprecated commands aren't listed
                cmd_name = line.strip().split()[0] if line.strip() else ""
                assert cmd_name not in deprecated, f"'{cmd_name}' should be hidden"


class TestBackwardsCompatibility:
    """Test backwards compatibility aliases."""

    def test_agents_alias_works(self, cli_runner):
        """Test 'kurt agents' forwards to 'kurt workflow' with warning."""
        result = cli_runner.invoke(main, ["agents", "--help"])
        assert result.exit_code == 0
        assert "deprecated" in result.output.lower()
        assert "workflow" in result.output

    def test_content_alias_works(self, cli_runner):
        """Test 'kurt content' forwards to 'kurt docs' with warning."""
        result = cli_runner.invoke(main, ["content", "--help"])
        assert result.exit_code == 0
        assert "deprecated" in result.output.lower()
        assert "docs" in result.output

    def test_show_alias_works(self, cli_runner):
        """Test 'kurt show' forwards to 'kurt help' with warning."""
        result = cli_runner.invoke(main, ["show", "--help"])
        assert result.exit_code == 0
        assert "deprecated" in result.output.lower()
        assert "help" in result.output

    def test_sync_alias_works(self, cli_runner):
        """Test 'kurt sync' forwards to 'kurt admin sync' with warning."""
        result = cli_runner.invoke(main, ["sync", "--help"])
        assert result.exit_code == 0
        assert "deprecated" in result.output.lower()
        assert "admin sync" in result.output
