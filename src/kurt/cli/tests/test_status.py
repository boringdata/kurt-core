"""Tests for status CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.status import status


class TestStatusCommand:
    """Tests for `kurt status` command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status command shows help."""
        result = invoke_cli(cli_runner, status, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show comprehensive Kurt project status")

    def test_status_shows_options(self, cli_runner: CliRunner):
        """Test status command lists options in help."""
        result = invoke_cli(cli_runner, status, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--format")
        assert_output_contains(result, "--hook-cc")

    def test_status_format_choices(self, cli_runner: CliRunner):
        """Test status --format accepts valid choices."""
        result = invoke_cli(cli_runner, status, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "pretty")
        assert_output_contains(result, "json")

    def test_status_not_initialized(self, cli_runner: CliRunner, cli_runner_isolated):
        """Test status shows message when not initialized."""
        result = invoke_cli(cli_runner, status, [])
        assert_cli_success(result)
        assert_output_contains(result, "not initialized")

    def test_status_json_not_initialized(self, cli_runner: CliRunner, cli_runner_isolated):
        """Test status --format json outputs JSON when not initialized."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)
        import json

        data = json.loads(result.output)
        assert data["initialized"] is False

    def test_status_with_database(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test status shows documents when database has data."""
        from unittest.mock import MagicMock, patch

        # Mock the config and database existence checks
        mock_config = MagicMock()
        mock_config.PATH_DB = str(tmp_project_with_docs / ".dolt")

        mock_status = {
            "initialized": True,
            "documents": {
                "total": 7,
                "by_status": {"fetched": 2, "not_fetched": 3, "error": 2, "skipped": 0},
                "by_domain": {"example.com": 7},
            },
        }
        with (
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
            patch("kurt.status.cli._get_status_data", return_value=mock_status),
        ):
            result = invoke_cli(cli_runner, status, ["--format", "json"])
            assert_cli_success(result)
            import json

            data = json.loads(result.output)
            assert data["initialized"] is True
            assert "documents" in data
            assert data["documents"]["total"] == 7


class TestStatusHookCC:
    """Tests for `kurt status --hook-cc` option."""

    def test_hook_cc_outputs_valid_json(self, cli_runner: CliRunner, tmp_project):
        """Test --hook-cc outputs valid JSON format for Claude Code hooks."""
        from unittest.mock import MagicMock, patch

        mock_config = MagicMock()
        mock_config.PATH_DB = str(tmp_project / ".dolt")

        with (
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
        ):
            result = invoke_cli(cli_runner, status, ["--hook-cc"])
            assert_cli_success(result)
            import json

            data = json.loads(result.output)
            assert "systemMessage" in data
            assert "hookSpecificOutput" in data
            assert "hookEventName" in data["hookSpecificOutput"]

    def test_hook_cc_with_documents(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test --hook-cc outputs document status when database has data."""
        from unittest.mock import MagicMock, patch

        mock_config = MagicMock()
        mock_config.PATH_DB = str(tmp_project_with_docs / ".dolt")

        mock_status = {
            "initialized": True,
            "documents": {
                "total": 7,
                "by_status": {"fetched": 2, "not_fetched": 3, "error": 2, "skipped": 0},
                "by_domain": {"example.com": 7},
            },
        }
        with (
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
            patch("kurt.status.cli._get_status_data", return_value=mock_status),
        ):
            result = invoke_cli(cli_runner, status, ["--hook-cc"])
            assert_cli_success(result)
            import json

            data = json.loads(result.output)
            assert "Documents" in data["systemMessage"]
            assert "additionalContext" in data["hookSpecificOutput"]


class TestStatusPrettyFormat:
    """Tests for `kurt status` pretty format output."""

    def test_status_pretty_with_project(self, cli_runner: CliRunner, tmp_project):
        """Test status pretty output with initialized project."""
        from unittest.mock import MagicMock, patch

        mock_config = MagicMock()
        mock_config.PATH_DB = str(tmp_project / ".dolt")

        mock_status = {
            "initialized": True,
            "documents": {"total": 0, "by_status": {}, "by_domain": {}},
        }
        with (
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
            patch("kurt.status.cli._get_status_data", return_value=mock_status),
        ):
            result = invoke_cli(cli_runner, status, [])
            assert_cli_success(result)
            # Pretty format should show markdown-style output
            assert "Kurt Status" in result.output or "Documents" in result.output

    def test_status_pretty_with_documents(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test status pretty output shows document counts."""
        from unittest.mock import MagicMock, patch

        mock_config = MagicMock()
        mock_config.PATH_DB = str(tmp_project_with_docs / ".dolt")

        mock_status = {
            "initialized": True,
            "documents": {
                "total": 7,
                "by_status": {"fetched": 2, "not_fetched": 3, "error": 2, "skipped": 0},
                "by_domain": {"example.com": 7},
            },
        }
        with (
            patch("kurt.config.config_file_exists", return_value=True),
            patch("kurt.config.load_config", return_value=mock_config),
            patch("kurt.status.cli._get_status_data", return_value=mock_status),
        ):
            result = invoke_cli(cli_runner, status, [])
            assert_cli_success(result)
            assert "Documents" in result.output
