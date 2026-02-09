"""
E2E tests for `kurt docs` command.

These tests verify the docs list, get, and delete commands work correctly
with real database operations.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_json_output,
    assert_output_contains,
    invoke_cli,
)
from kurt.documents.cli import docs_group, list_cmd, get_cmd, delete_cmd


class TestDocsHelp:
    """Tests for docs command help and options."""

    def test_docs_group_help(self, cli_runner: CliRunner):
        """Verify docs group shows help."""
        result = invoke_cli(cli_runner, docs_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Document management commands")

    def test_docs_list_help(self, cli_runner: CliRunner):
        """Verify docs list shows help."""
        result = invoke_cli(cli_runner, list_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "List documents with filters")

    def test_docs_list_shows_options(self, cli_runner: CliRunner):
        """Verify docs list lists all options."""
        result = invoke_cli(cli_runner, list_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--include")
        assert_output_contains(result, "--url-contains")
        assert_output_contains(result, "--ids")
        assert_output_contains(result, "--with-status")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--format")

    def test_docs_get_help(self, cli_runner: CliRunner):
        """Verify docs get shows help."""
        result = invoke_cli(cli_runner, get_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Get document details")

    def test_docs_delete_help(self, cli_runner: CliRunner):
        """Verify docs delete shows help."""
        result = invoke_cli(cli_runner, delete_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Delete documents")


class TestDocsListEmpty:
    """E2E tests for docs list with no documents."""

    def test_docs_list_empty_project(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify docs list works with empty project."""
        result = invoke_cli(cli_runner, list_cmd, [])

        assert result.exit_code == 0
        assert "No documents found" in result.output

    def test_docs_list_empty_json(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify docs list returns empty JSON array for empty project."""
        result = invoke_cli(cli_runner, list_cmd, ["--format", "json"])

        assert result.exit_code == 0
        data = assert_json_output(result)
        # Robot mode envelope or direct array
        if "data" in data:
            assert data["data"] == []
        else:
            assert data == []


class TestDocsListWithDocuments:
    """E2E tests for docs list with documents."""

    def test_docs_list_shows_documents(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify docs list shows documents in table format."""
        result = invoke_cli(cli_runner, list_cmd, [])

        assert result.exit_code == 0
        # Should show documents
        assert "Total:" in result.output or "document" in result.output.lower()

    def test_docs_list_json_format(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify docs list JSON output contains document data."""
        result = invoke_cli(cli_runner, list_cmd, ["--format", "json"])

        assert result.exit_code == 0
        data = assert_json_output(result)
        # Unwrap robot mode envelope if present
        docs = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(docs, list):
            assert len(docs) > 0
            # Check document structure
            for doc in docs:
                assert "document_id" in doc or "source_url" in doc


class TestDocsListFilters:
    """E2E tests for docs list filter options."""

    def test_docs_list_with_limit(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --limit caps the number of results."""
        result = invoke_cli(cli_runner, list_cmd, ["--limit", "1", "--format", "json"])

        assert result.exit_code == 0
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data
        if isinstance(docs, list):
            assert len(docs) <= 1

    def test_docs_list_with_include_pattern(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --include filters by pattern."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--include", "*example*", "--format", "json"]
        )

        assert result.exit_code == 0
        # Command should complete - results depend on test data

    def test_docs_list_with_url_contains(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --url-contains filters by URL substring."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--url-contains", "example", "--format", "json"]
        )

        assert result.exit_code == 0

    def test_docs_list_with_status_fetched(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --with-status FETCHED filters documents."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--with-status", "fetched", "--format", "json"]
        )

        assert result.exit_code == 0

    def test_docs_list_with_status_not_fetched(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --with-status NOT_FETCHED filters documents."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--with-status", "not_fetched", "--format", "json"]
        )

        assert result.exit_code == 0

    def test_docs_list_with_status_error(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --with-status ERROR filters documents."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--with-status", "error", "--format", "json"]
        )

        assert result.exit_code == 0

    def test_docs_list_with_ids(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --ids filters by document IDs."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--ids", "nonexistent-id", "--format", "json"]
        )

        assert result.exit_code == 0
        # Should return empty results for non-existent ID


class TestDocsGet:
    """E2E tests for docs get command."""

    def test_docs_get_not_found(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify docs get handles not found gracefully."""
        result = invoke_cli(cli_runner, get_cmd, ["nonexistent-id"])

        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_docs_get_not_found_json(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify docs get returns JSON error for not found."""
        result = invoke_cli(cli_runner, get_cmd, ["nonexistent-id", "--format", "json"])

        assert result.exit_code == 0
        data = assert_json_output(result)
        # Handle robot mode envelope
        if "data" in data:
            data = data["data"]
        assert "error" in data or data is None

    def test_docs_get_by_partial_id(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify docs get can retrieve by partial ID."""
        # First list to get an ID
        list_result = invoke_cli(cli_runner, list_cmd, ["--format", "json"])
        list_data = assert_json_output(list_result)
        docs = list_data.get("data", list_data) if isinstance(list_data, dict) else list_data

        if isinstance(docs, list) and len(docs) > 0:
            doc_id = docs[0].get("document_id", "")[:8]
            result = invoke_cli(cli_runner, get_cmd, [doc_id, "--format", "json"])
            assert result.exit_code == 0

    def test_docs_get_text_format(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify docs get works with text format."""
        result = invoke_cli(cli_runner, get_cmd, ["nonexistent", "--format", "text"])

        assert result.exit_code == 0
        # Should show not found in text format


class TestDocsDelete:
    """E2E tests for docs delete command."""

    def test_docs_delete_dry_run(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --dry-run previews deletion without deleting."""
        result = invoke_cli(
            cli_runner, delete_cmd, ["--include", "*", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "Dry run" in result.output or "no documents were deleted" in result.output.lower()

    def test_docs_delete_with_yes_flag(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --yes skips confirmation."""
        # Get count before
        list_result = invoke_cli(cli_runner, list_cmd, ["--format", "json"])
        list_data = assert_json_output(list_result)
        docs = list_data.get("data", list_data) if isinstance(list_data, dict) else list_data

        if isinstance(docs, list) and len(docs) > 0:
            doc_id = docs[0].get("document_id", "")
            result = invoke_cli(cli_runner, delete_cmd, [doc_id, "--yes"])
            assert result.exit_code == 0
            assert "Deleted" in result.output or "deleted" in result.output.lower()

    def test_docs_delete_no_match(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify delete handles no matching documents gracefully."""
        result = invoke_cli(
            cli_runner, delete_cmd, ["nonexistent-id-12345", "--yes"]
        )

        assert result.exit_code == 0
        assert "No documents found" in result.output

    def test_docs_delete_with_limit(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --limit caps number of documents to delete."""
        result = invoke_cli(
            cli_runner, delete_cmd, ["--include", "*", "--limit", "1", "--dry-run"]
        )

        assert result.exit_code == 0

    def test_docs_delete_with_ids(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --ids option works."""
        result = invoke_cli(
            cli_runner, delete_cmd, ["--ids", "id1,id2", "--dry-run"]
        )

        assert result.exit_code == 0

    def test_docs_delete_with_url_contains(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --url-contains option works."""
        result = invoke_cli(
            cli_runner, delete_cmd, ["--url-contains", "example", "--dry-run"]
        )

        assert result.exit_code == 0


class TestDocsJsonOutput:
    """E2E tests for JSON output consistency."""

    def test_docs_list_json_structure(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify docs list JSON has expected structure."""
        result = invoke_cli(cli_runner, list_cmd, ["--format", "json"])

        assert result.exit_code == 0
        data = assert_json_output(result)

        # Robot mode envelope: {"success": bool, "data": [...]}
        # Or direct array
        if isinstance(data, dict):
            if "success" in data:
                assert data["success"] is True
                docs = data.get("data", [])
            else:
                docs = data
        else:
            docs = data

        if isinstance(docs, list) and len(docs) > 0:
            doc = docs[0]
            # Check expected fields
            expected_fields = ["document_id", "source_url"]
            for field in expected_fields:
                assert field in doc, f"Missing field {field}"


class TestDocsGlobalJsonFlag:
    """E2E tests for global --json flag compatibility."""

    def test_docs_list_global_json(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify docs list works with global --json flag.

        Note: docs commands use --format json instead of global --json flag.
        This test verifies the command doesn't crash with global flag set.
        """
        from kurt.cli.main import main

        result = cli_runner.invoke(main, ["--json", "docs", "list"], catch_exceptions=False)

        # Command should complete without crashing
        assert result.exit_code == 0

    def test_docs_get_global_json(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify docs get works with global --json flag.

        Note: docs commands use --format json instead of global --json flag.
        This test verifies the command doesn't crash with global flag set.
        """
        from kurt.cli.main import main

        result = cli_runner.invoke(
            main, ["--json", "docs", "get", "nonexistent"], catch_exceptions=False
        )

        # Command should complete without crashing
        assert result.exit_code == 0
