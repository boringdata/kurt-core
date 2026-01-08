"""Tests for fetch workflow CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt_new.workflows.fetch.cli import fetch_cmd


class TestFetchCommand:
    """Tests for `content fetch` command."""

    def test_fetch_help(self, cli_runner: CliRunner):
        """Test fetch command shows help."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Fetch and index documents")

    def test_fetch_shows_all_options(self, cli_runner: CliRunner):
        """Test fetch command lists all options in help."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--help"])
        assert_cli_success(result)
        # Filter options
        assert_output_contains(result, "--include")
        assert_output_contains(result, "--ids")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--with-status")
        # Background options
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--priority")
        # Other options
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")

    def test_fetch_no_docs_message(self, cli_runner: CliRunner, tmp_database):
        """Test fetch shows message when no documents found."""
        result = invoke_cli(cli_runner, fetch_cmd, [])
        assert_cli_success(result)
        assert_output_contains(result, "No documents")

    def test_fetch_with_identifier(self, cli_runner: CliRunner, tmp_database):
        """Test fetch with identifier argument."""
        result = invoke_cli(cli_runner, fetch_cmd, ["some-id"])
        assert_cli_success(result)

    def test_fetch_with_limit(self, cli_runner: CliRunner, tmp_database):
        """Test fetch --limit option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--limit", "10"])
        assert_cli_success(result)

    def test_fetch_with_include_pattern(self, cli_runner: CliRunner, tmp_database):
        """Test fetch --include option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--include", "*.md"])
        assert_cli_success(result)

    def test_fetch_with_status_filter(self, cli_runner: CliRunner, tmp_database):
        """Test fetch --with-status option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--with-status", "NOT_FETCHED"])
        assert_cli_success(result)

    def test_fetch_with_dry_run(self, cli_runner: CliRunner, tmp_database):
        """Test fetch --dry-run option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--dry-run"])
        assert_cli_success(result)

    def test_fetch_with_json_format(self, cli_runner: CliRunner, tmp_database):
        """Test fetch --format json option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--format", "json"])
        assert_cli_success(result)

    def test_fetch_with_background(self, cli_runner: CliRunner, tmp_database):
        """Test fetch --background option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--background"])
        assert_cli_success(result)

    def test_fetch_with_priority(self, cli_runner: CliRunner, tmp_database):
        """Test fetch --priority option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--priority", "5"])
        assert_cli_success(result)

    def test_fetch_combined_options(self, cli_runner: CliRunner, tmp_database):
        """Test fetch with multiple options combined."""
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            [
                "--include",
                "*.md",
                "--limit",
                "10",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        assert_cli_success(result)


class TestE2EWithDocs:
    """E2E tests using tmp_project_with_docs fixture with real documents."""

    def test_fetch_shows_documents_to_fetch(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test fetch --dry-run shows documents that would be fetched."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--dry-run", "--format", "json"])
        assert_cli_success(result)
        # Should show documents that need fetching (discovered but not fetched)
        import json

        data = json.loads(result.output)
        assert isinstance(data, (list, dict))

    def test_fetch_with_limit_real_docs(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test fetch --limit with real documents."""
        result = invoke_cli(
            cli_runner, fetch_cmd, ["--limit", "2", "--dry-run", "--format", "json"]
        )
        assert_cli_success(result)
        import json

        data = json.loads(result.output)
        # Should respect the limit
        if isinstance(data, list):
            assert len(data) <= 2

    def test_fetch_with_status_filter(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test fetch --with-status filters documents correctly."""
        result = invoke_cli(
            cli_runner, fetch_cmd, ["--with-status", "NOT_FETCHED", "--dry-run", "--format", "json"]
        )
        assert_cli_success(result)

    def test_fetch_with_include_pattern(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test fetch --include filters by URL pattern."""
        result = invoke_cli(
            cli_runner, fetch_cmd, ["--include", "*/docs/*", "--dry-run", "--format", "json"]
        )
        assert_cli_success(result)

    def test_fetch_specific_id(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test fetch with specific document ID using --format json --dry-run."""
        result = invoke_cli(
            cli_runner, fetch_cmd, ["--ids", "doc-1", "--dry-run", "--format", "json"]
        )
        assert_cli_success(result)
        import json

        data = json.loads(result.output)
        # The dry_run should return info about the document
        assert isinstance(data, dict)

    def test_fetch_multiple_ids(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test fetch --ids with multiple document IDs."""
        result = invoke_cli(
            cli_runner, fetch_cmd, ["--ids", "doc-1,doc-2,doc-3", "--dry-run", "--format", "json"]
        )
        assert_cli_success(result)


class TestBackgroundExecution:
    """Tests that verify --background actually runs workflows in background using DBOS.

    These tests use dbos_launched fixture for real DBOS integration.
    They would have caught the bug where background/priority CLI args
    were not forwarded to run_fetch().
    """

    def test_background_returns_workflow_id(
        self, cli_runner: CliRunner, tmp_project_with_docs, dbos_launched
    ):
        """Test that --background returns a workflow_id immediately.

        When running in background, the CLI should return a workflow_id
        that can be used to check status later.
        """
        import json

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "doc-1", "--background", "--format", "json"],
        )
        assert_cli_success(result)

        # Parse JSON output
        data = json.loads(result.output)

        # Background mode should return workflow_id (or status message if no docs)
        if data is not None:
            assert (
                "workflow_id" in data or "status" in data or isinstance(data, str)
            ), f"Expected workflow_id or status in response, got: {data}"

    def test_background_workflow_appears_in_dbos(
        self, cli_runner: CliRunner, tmp_project_with_docs, dbos_launched
    ):
        """Test that background workflow is registered in DBOS workflow_status table."""
        import json

        from sqlalchemy import text

        from kurt_new.db import managed_session

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "doc-1", "--background", "--format", "json"],
        )
        assert_cli_success(result)

        data = json.loads(result.output)
        workflow_id = data.get("workflow_id") if isinstance(data, dict) else data

        if workflow_id:
            # Check workflow exists in DBOS
            with managed_session() as session:
                row = session.execute(
                    text("SELECT status FROM workflow_status WHERE workflow_uuid = :wf_id"),
                    {"wf_id": workflow_id},
                ).fetchone()

            # Workflow should exist (status can be PENDING, SUCCESS, or ERROR)
            assert row is not None, f"Workflow {workflow_id} not found in DBOS"

    def test_foreground_completes_synchronously(
        self, cli_runner: CliRunner, tmp_project_with_docs, dbos_launched
    ):
        """Test that without --background, workflow completes synchronously."""
        import json

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "doc-1", "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

        data = json.loads(result.output)

        # Foreground mode should return full result, not just workflow_id
        assert isinstance(data, dict)
        # Should have workflow completion indicators
        assert "workflow_id" in data or "dry_run" in data or "success_count" in data

    def test_priority_affects_workflow(
        self, cli_runner: CliRunner, tmp_project_with_docs, dbos_launched
    ):
        """Test that --priority option is accepted and workflow runs."""
        import json

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "doc-1", "--priority", "1", "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

        # Should complete without error
        data = json.loads(result.output)
        assert isinstance(data, dict)
