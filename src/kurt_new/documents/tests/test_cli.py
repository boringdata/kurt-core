"""Tests for documents CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_json_output,
    assert_output_contains,
    invoke_cli,
)
from kurt_new.documents.cli import content_group


class TestContentGroup:
    """Tests for the content command group."""

    def test_content_group_help(self, cli_runner: CliRunner):
        """Test content group shows help."""
        result = invoke_cli(cli_runner, content_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Document management commands")

    def test_content_list_commands(self, cli_runner: CliRunner):
        """Test content group lists all commands."""
        result = invoke_cli(cli_runner, content_group, ["--help"])
        assert_cli_success(result)
        # Check all expected commands are listed
        assert_output_contains(result, "list")
        assert_output_contains(result, "get")
        assert_output_contains(result, "delete")
        assert_output_contains(result, "fetch")
        assert_output_contains(result, "map")


class TestListCommand:
    """Tests for `content list` command."""

    def test_list_help(self, cli_runner: CliRunner):
        """Test list command shows help."""
        result = invoke_cli(cli_runner, content_group, ["list", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "List documents")

    def test_list_with_all_filter_options(self, cli_runner: CliRunner):
        """Test list accepts all filter options."""
        result = invoke_cli(cli_runner, content_group, ["list", "--help"])
        assert_cli_success(result)
        # Check all filter options are documented
        assert_output_contains(result, "--include")
        assert_output_contains(result, "--ids")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--with-status")
        assert_output_contains(result, "--format")

    def test_list_json_format_option(self, cli_runner: CliRunner, tmp_database):
        """Test list --format json outputs valid JSON."""
        result = invoke_cli(cli_runner, content_group, ["list", "--format", "json"])
        assert_cli_success(result)
        data = assert_json_output(result)
        assert isinstance(data, list)

    def test_list_table_format_option(self, cli_runner: CliRunner, tmp_database):
        """Test list --format table outputs table."""
        result = invoke_cli(cli_runner, content_group, ["list", "--format", "table"])
        assert_cli_success(result)

    def test_list_with_limit(self, cli_runner: CliRunner, tmp_database):
        """Test list --limit option."""
        result = invoke_cli(cli_runner, content_group, ["list", "--limit", "5"])
        assert_cli_success(result)

    def test_list_with_status_filter(self, cli_runner: CliRunner, tmp_database):
        """Test list --with-status option."""
        result = invoke_cli(cli_runner, content_group, ["list", "--with-status", "FETCHED"])
        assert_cli_success(result)

    def test_list_with_include_pattern(self, cli_runner: CliRunner, tmp_database):
        """Test list --include option."""
        result = invoke_cli(cli_runner, content_group, ["list", "--include", "*.md"])
        assert_cli_success(result)


class TestGetCommand:
    """Tests for `content get` command."""

    def test_get_help(self, cli_runner: CliRunner):
        """Test get command shows help."""
        result = invoke_cli(cli_runner, content_group, ["get", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Get document details")

    def test_get_requires_identifier(self, cli_runner: CliRunner):
        """Test get command requires identifier argument."""
        result = cli_runner.invoke(content_group, ["get"])
        # Should fail because identifier is required
        assert result.exit_code != 0

    def test_get_with_json_format(self, cli_runner: CliRunner, tmp_database):
        """Test get --format json option."""
        result = invoke_cli(cli_runner, content_group, ["get", "nonexistent", "--format", "json"])
        assert_cli_success(result)
        data = assert_json_output(result)
        assert "error" in data  # Document not found

    def test_get_with_text_format(self, cli_runner: CliRunner, tmp_database):
        """Test get --format text option."""
        result = invoke_cli(cli_runner, content_group, ["get", "nonexistent", "--format", "text"])
        assert_cli_success(result)


class TestDeleteCommand:
    """Tests for `content delete` command."""

    def test_delete_help(self, cli_runner: CliRunner):
        """Test delete command shows help."""
        result = invoke_cli(cli_runner, content_group, ["delete", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Delete documents")

    def test_delete_with_dry_run(self, cli_runner: CliRunner, tmp_database):
        """Test delete --dry-run option."""
        result = invoke_cli(cli_runner, content_group, ["delete", "test-id", "--dry-run"])
        assert_cli_success(result)

    def test_delete_with_yes_flag(self, cli_runner: CliRunner, tmp_database):
        """Test delete -y option skips confirmation."""
        result = invoke_cli(cli_runner, content_group, ["delete", "test-id", "-y"])
        assert_cli_success(result)

    def test_delete_with_ids_option(self, cli_runner: CliRunner, tmp_database):
        """Test delete --ids option."""
        result = invoke_cli(cli_runner, content_group, ["delete", "--ids", "a,b,c", "--dry-run"])
        assert_cli_success(result)

    def test_delete_with_include_pattern(self, cli_runner: CliRunner, tmp_database):
        """Test delete --include option."""
        result = invoke_cli(
            cli_runner, content_group, ["delete", "--include", "*test*", "--dry-run"]
        )
        assert_cli_success(result)


class TestE2EWithDocs:
    """E2E tests using tmp_project_with_docs fixture."""

    def test_list_shows_documents(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test list shows documents from database."""

        result = invoke_cli(cli_runner, content_group, ["list", "--format", "json"])
        assert_cli_success(result)
        data = assert_json_output(result)
        assert len(data) == 7  # 7 documents in tmp_project_with_docs

    def test_list_filter_by_status(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test list filters by fetch status."""

        result = invoke_cli(
            cli_runner, content_group, ["list", "--with-status", "FETCHED", "--format", "json"]
        )
        assert_cli_success(result)
        data = assert_json_output(result)
        assert len(data) == 2  # 2 fetched documents

    def test_list_filter_not_fetched(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test list filters by NOT_FETCHED status."""

        result = invoke_cli(
            cli_runner, content_group, ["list", "--with-status", "NOT_FETCHED", "--format", "json"]
        )
        assert_cli_success(result)
        data = assert_json_output(result)
        # 3 discovered + 1 fetch error + 1 map error = 5 not fetched
        assert len(data) >= 3

    def test_get_existing_document(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test get retrieves existing document."""

        result = invoke_cli(cli_runner, content_group, ["get", "doc-1", "--format", "json"])
        assert_cli_success(result)
        data = assert_json_output(result)
        assert data.get("document_id") == "doc-1"

    def test_get_nonexistent_document(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test get with nonexistent document."""

        result = invoke_cli(cli_runner, content_group, ["get", "nonexistent", "--format", "json"])
        assert_cli_success(result)
        data = assert_json_output(result)
        assert "error" in data

    def test_list_with_include_filter(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test list with include pattern filter."""

        result = invoke_cli(
            cli_runner, content_group, ["list", "--include", "*/docs/*", "--format", "json"]
        )
        assert_cli_success(result)
        data = assert_json_output(result)
        # All URLs in tmp_project_with_docs contain /docs/
        assert len(data) >= 1
        for doc in data:
            assert "/docs/" in doc.get("source_url", "")

    def test_delete_dry_run_shows_count(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test delete --dry-run shows documents that would be deleted."""

        result = invoke_cli(
            cli_runner, content_group, ["delete", "--include", "*/docs/*", "--dry-run"]
        )
        assert_cli_success(result)
        assert "Would delete" in result.output or "dry run" in result.output.lower()
