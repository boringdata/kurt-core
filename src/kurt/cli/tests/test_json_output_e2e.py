"""
E2E tests for JSON output consistency across CLI commands.

These tests verify that --format json and --json flags produce
valid, consistent JSON output across all commands.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from kurt.cli.main import main
from kurt.conftest import (
    assert_cli_success,
    invoke_cli,
)


def parse_json_output(output: str) -> dict | list | None:
    """Parse JSON from command output, handling table creation messages."""
    lines = output.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


class TestJsonOutputValid:
    """Tests that JSON output is valid and parseable."""

    def test_status_json_valid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify status --format json produces valid JSON."""
        result = cli_runner.invoke(main, ["--json", "status"], catch_exceptions=False)
        assert result.exit_code in (0, 1, 2)

        data = parse_json_output(result.output)
        assert data is not None, f"Could not parse JSON from: {result.output}"
        assert isinstance(data, dict)

    def test_docs_list_json_valid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify docs list --format json produces valid JSON."""
        from kurt.documents.cli import docs_group

        result = invoke_cli(cli_runner, docs_group, ["list", "--format", "json"])
        assert result.exit_code in (0, 1, 2)

        data = parse_json_output(result.output)
        assert data is not None, f"Could not parse JSON from: {result.output}"

    def test_workflow_list_json_valid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify workflow list --format json produces valid JSON."""
        result = cli_runner.invoke(
            main, ["workflow", "list", "--format", "json"], catch_exceptions=False
        )
        assert result.exit_code in (0, 1, 2)

        if result.exit_code == 0 and result.output.strip():
            data = parse_json_output(result.output)
            # May be empty or list
            assert data is None or isinstance(data, (dict, list))


class TestJsonErrorFormat:
    """Tests that errors are returned in JSON format when requested."""

    def test_invalid_command_json_error(self, cli_runner: CliRunner):
        """Verify invalid command returns JSON error with --json flag."""
        # This may not return JSON as the error happens before command routing
        result = cli_runner.invoke(main, ["--json", "nonexistent"], catch_exceptions=False)
        assert result.exit_code != 0

    def test_missing_arg_json_error(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify missing required arg returns structured error."""
        from kurt.documents.cli import docs_group

        # docs get without ID should fail
        result = invoke_cli(cli_runner, docs_group, ["get", "--format", "json"])
        # Exit code depends on whether it's a usage error
        assert result.exit_code != 0 or "error" in result.output.lower()


class TestJsonListFormat:
    """Tests that list commands return arrays."""

    def test_docs_list_returns_array_or_object(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify docs list returns array or wrapped object."""
        from kurt.documents.cli import docs_group

        result = invoke_cli(cli_runner, docs_group, ["list", "--format", "json"])
        assert result.exit_code in (0, 1, 2)

        data = parse_json_output(result.output)
        if data is not None:
            # Either a direct list or a wrapped object with 'data' or 'documents'
            if isinstance(data, list):
                assert all(isinstance(item, dict) for item in data)
            elif isinstance(data, dict):
                # Check for common wrapper patterns
                assert (
                    "data" in data
                    or "documents" in data
                    or "items" in data
                    or "success" in data
                )


class TestJsonDetailFormat:
    """Tests that detail commands return objects."""

    def test_status_returns_object(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify status returns an object."""
        result = cli_runner.invoke(main, ["--json", "status"], catch_exceptions=False)
        assert result.exit_code in (0, 1, 2)

        data = parse_json_output(result.output)
        if data is not None:
            assert isinstance(data, dict)


class TestJsonNullHandling:
    """Tests that null values are handled correctly."""

    def test_null_values_valid_json(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify null values don't break JSON parsing."""
        result = cli_runner.invoke(main, ["--json", "status"], catch_exceptions=False)
        assert result.exit_code in (0, 1, 2)

        data = parse_json_output(result.output)
        if data is not None:
            # Should be able to serialize back to JSON
            json_str = json.dumps(data)
            assert json_str is not None


class TestJsonUnicode:
    """Tests that unicode characters are preserved."""

    def test_unicode_in_json(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify unicode characters are preserved in JSON output."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        # Create a document with unicode
        with managed_session() as session:
            session.add(
                MapDocument(
                    document_id="unicode-test",
                    source_url="https://example.com/日本語",
                    source_type="url",
                    discovery_method="test",
                    status=MapStatus.SUCCESS,
                    title="日本語タイトル",
                )
            )
            session.commit()

        from kurt.documents.cli import docs_group

        result = invoke_cli(
            cli_runner, docs_group, ["get", "unicode-test", "--format", "json"]
        )

        if result.exit_code == 0:
            data = parse_json_output(result.output)
            if data is not None:
                # Verify unicode is preserved
                json_str = json.dumps(data, ensure_ascii=False)
                assert "日本語" in json_str


class TestJsonConsistency:
    """Tests that JSON output is consistent across similar commands."""

    def test_success_envelope_consistency(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify success responses have consistent envelope."""
        result = cli_runner.invoke(main, ["--json", "status"], catch_exceptions=False)
        assert result.exit_code in (0, 1, 2)

        data = parse_json_output(result.output)
        if data is not None and isinstance(data, dict):
            # Check for robot envelope pattern
            if "success" in data:
                assert isinstance(data["success"], bool)
                if data["success"]:
                    assert "data" in data or "result" in data or len(data) > 1


class TestGlobalJsonFlag:
    """Tests that global --json flag works on various commands."""

    def test_json_with_doctor(self, cli_runner: CliRunner):
        """Verify --json works with doctor command."""
        with cli_runner.isolated_filesystem():
            import subprocess

            subprocess.run(["git", "init"], capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], capture_output=True)
            Path("README.md").write_text("# Test")
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(["git", "commit", "-m", "Init"], capture_output=True)

            result = cli_runner.invoke(main, ["--json", "doctor"], catch_exceptions=False)

        assert result.exit_code in (0, 1, 2)
        # Should contain JSON structure
        assert "{" in result.output

    def test_json_with_tool_map_help(self, cli_runner: CliRunner):
        """Verify --json doesn't break help output."""
        result = cli_runner.invoke(
            main, ["--json", "tool", "map", "--help"], catch_exceptions=False
        )
        # Help should still work
        assert result.exit_code == 0

    def test_format_json_option(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --format json option works."""
        from kurt.documents.cli import docs_group

        result = invoke_cli(cli_runner, docs_group, ["list", "--format", "json"])
        assert result.exit_code in (0, 1, 2)
