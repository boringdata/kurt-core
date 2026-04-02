"""
E2E tests for `kurt status` command.

These tests use real filesystem and Dolt database operations,
verifying that status reflects actual database state.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_json_output,
    assert_output_contains,
    invoke_cli,
)
from kurt.status import status


@pytest.fixture
def dolt_available() -> bool:
    """Check if Dolt is installed."""
    return shutil.which("dolt") is not None


@pytest.fixture
def tmp_status_project(tmp_project: Path) -> Path:
    """
    Temporary project with correct config for status command.

    The tmp_project fixture uses create_config() which sets PATH_DB to sqlite,
    but the status command expects a Dolt-compatible config. This fixture
    rewrites the config to match what `kurt init` creates.
    """
    import uuid

    config_path = tmp_project / "kurt.toml"
    workspace_id = str(uuid.uuid4())

    config_content = f'''# Kurt Project Configuration
# Auto-generated for testing

[workspace]
id = "{workspace_id}"

[paths]
db = ".dolt"
sources = "sources"
projects = "projects"
rules = "rules"
workflows = "workflows"

[telemetry]
enabled = false
'''
    config_path.write_text(config_content)
    return tmp_project


@pytest.fixture
def tmp_status_project_with_docs(tmp_project_with_docs: Path) -> Path:
    """
    Project with documents and correct config for status command.
    """
    import uuid

    config_path = tmp_project_with_docs / "kurt.toml"
    workspace_id = str(uuid.uuid4())

    config_content = f'''# Kurt Project Configuration
# Auto-generated for testing

[workspace]
id = "{workspace_id}"

[paths]
db = ".dolt"
sources = "sources"
projects = "projects"
rules = "rules"
workflows = "workflows"

[telemetry]
enabled = false
'''
    config_path.write_text(config_content)
    return tmp_project_with_docs


class TestStatusNotInitialized:
    """E2E tests for status when project is not initialized."""

    def test_status_not_initialized(self, cli_runner: CliRunner, cli_runner_isolated):
        """Verify status shows not initialized message."""
        result = invoke_cli(cli_runner, status, [])
        assert_cli_success(result)
        assert_output_contains(result, "not initialized")

    def test_status_not_initialized_json(self, cli_runner: CliRunner, cli_runner_isolated):
        """Verify status --format json shows not initialized."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        # Robot envelope: error case uses {"success": false, "error": {...}}
        if "error" in data:
            assert data["success"] is False
            assert data["error"]["code"] == "NOT_INITIALIZED"
        else:
            # Direct output without envelope
            inner = data.get("data", data)
            assert inner.get("initialized") is False


class TestStatusEmptyProject:
    """E2E tests for status with initialized project but no documents."""

    def test_status_empty_project(self, cli_runner: CliRunner, tmp_status_project):
        """Verify status with no documents shows zero counts."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        # Robot envelope: success wraps data
        if "data" in data and "success" in data:
            data = data["data"]

        assert data["initialized"] is True
        assert data["documents"]["total"] == 0
        assert data["documents"]["by_status"].get("fetched", 0) == 0
        assert data["documents"]["by_domain"] == {}

    def test_status_empty_project_pretty(self, cli_runner: CliRunner, tmp_status_project):
        """Verify status pretty format works with empty project."""
        result = invoke_cli(cli_runner, status, [])
        assert_cli_success(result)

        # Pretty format should still show Documents section
        assert "Documents" in result.output or "documents" in result.output.lower()


class TestStatusWithDocuments:
    """E2E tests for status with documents in database."""

    def test_status_shows_document_counts(self, cli_runner: CliRunner, tmp_status_project_with_docs):
        """Verify status shows correct document counts."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        # Robot envelope: success wraps data
        if "data" in data and "success" in data:
            data = data["data"]

        assert data["initialized"] is True
        docs = data["documents"]

        # tmp_project_with_docs creates:
        # - 7 MapDocuments total
        # - 2 with FetchDocument.SUCCESS
        # - 1 with FetchDocument.ERROR
        # - 4 MapDocuments without corresponding FetchDocument (pending)
        assert docs["total"] >= 7

        by_status = docs["by_status"]
        assert by_status["fetched"] == 2  # SUCCESS fetch documents
        assert by_status["error"] == 1  # ERROR fetch documents
        # not_fetched includes documents without FetchDocument
        assert by_status["not_fetched"] >= 3

    def test_status_shows_domain_counts(self, cli_runner: CliRunner, tmp_status_project_with_docs):
        """Verify status shows document counts by domain."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        by_domain = data["documents"]["by_domain"]
        # All test documents are from example.com
        assert "example.com" in by_domain
        assert by_domain["example.com"] >= 7

    def test_status_pretty_shows_documents(self, cli_runner: CliRunner, tmp_status_project_with_docs):
        """Verify status pretty format shows document information."""
        result = invoke_cli(cli_runner, status, [])
        assert_cli_success(result)

        # Should mention documents
        assert "Documents" in result.output or "documents" in result.output.lower()


class TestStatusJsonOutput:
    """E2E tests for status JSON output format."""

    def test_status_json_is_valid(self, cli_runner: CliRunner, tmp_status_project):
        """Verify status --format json outputs valid JSON."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        # Should have success or error structure
        assert "success" in data or "initialized" in data

    def test_status_json_has_required_fields(self, cli_runner: CliRunner, tmp_status_project_with_docs):
        """Verify status JSON contains all required fields."""
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        assert "initialized" in data
        assert "documents" in data
        assert "total" in data["documents"]
        assert "by_status" in data["documents"]
        assert "by_domain" in data["documents"]

    def test_status_global_json_flag(self, cli_runner: CliRunner, tmp_status_project):
        """Verify global --json flag works with status."""

        from kurt.cli.main import main

        result = cli_runner.invoke(main, ["--json", "status"], catch_exceptions=False)
        assert_cli_success(result)

        # The main CLI may print table creation messages before JSON
        # Find the JSON line in output
        output_lines = result.output.strip().split("\n")
        json_line = None
        for line in output_lines:
            if line.startswith("{"):
                json_line = line
                break

        assert json_line is not None, f"No JSON found in output: {result.output}"
        data = json.loads(json_line)
        # Should have success wrapper
        assert "success" in data


class TestStatusHookCC:
    """E2E tests for status --hook-cc output format."""

    def test_hook_cc_valid_json(self, cli_runner: CliRunner, tmp_status_project):
        """Verify --hook-cc outputs valid JSON."""
        result = invoke_cli(cli_runner, status, ["--hook-cc"])
        assert_cli_success(result)

        data = assert_json_output(result)
        # Hook format has systemMessage and hookSpecificOutput
        assert "systemMessage" in data
        assert "hookSpecificOutput" in data

    def test_hook_cc_has_required_fields(self, cli_runner: CliRunner, tmp_status_project):
        """Verify --hook-cc has all required hook fields."""
        result = invoke_cli(cli_runner, status, ["--hook-cc"])
        assert_cli_success(result)

        data = assert_json_output(result)
        assert "systemMessage" in data
        assert "hookSpecificOutput" in data
        assert "hookEventName" in data["hookSpecificOutput"]
        assert "additionalContext" in data["hookSpecificOutput"]

    def test_hook_cc_with_documents(self, cli_runner: CliRunner, tmp_status_project_with_docs):
        """Verify --hook-cc includes document status."""
        result = invoke_cli(cli_runner, status, ["--hook-cc"])
        assert_cli_success(result)

        data = assert_json_output(result)
        # systemMessage should mention documents
        assert "Documents" in data["systemMessage"]

    def test_hook_cc_not_initialized_auto_inits(self, cli_runner: CliRunner, cli_runner_isolated, dolt_available):
        """Verify --hook-cc auto-initializes project when not initialized."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner, status, ["--hook-cc"])
        assert_cli_success(result)

        data = assert_json_output(result)
        # Should have initialized the project
        assert "initialized" in data["systemMessage"].lower()
        # kurt.toml should now exist
        assert (Path.cwd() / "kurt.toml").exists()


class TestStatusDatabaseIntegration:
    """E2E tests verifying status matches actual database state."""

    def test_status_reflects_database_counts(self, cli_runner: CliRunner, tmp_status_project):
        """Verify status counts match database after adding documents."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        # Add documents directly to database
        with managed_session() as session:
            for i in range(5):
                session.add(
                    MapDocument(
                        document_id=f"test-doc-{i}",
                        source_url=f"https://test.example.com/page{i}",
                        source_type="url",
                        discovery_method="sitemap",
                        status=MapStatus.SUCCESS,
                        title=f"Test Page {i}",
                    )
                )
            session.commit()

        # Check status reflects the documents
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        assert data["documents"]["total"] == 5
        assert data["documents"]["by_domain"]["test.example.com"] == 5

    def test_status_reflects_fetch_status_changes(self, cli_runner: CliRunner, tmp_status_project):
        """Verify status updates when fetch statuses change."""
        from kurt.db import managed_session
        from kurt.tools.fetch.models import FetchDocument, FetchStatus
        from kurt.tools.map.models import MapDocument, MapStatus

        # Add a map document and corresponding fetch document
        with managed_session() as session:
            session.add(
                MapDocument(
                    document_id="fetch-test-1",
                    source_url="https://fetch.example.com/doc1",
                    source_type="url",
                    discovery_method="crawl",
                    status=MapStatus.SUCCESS,
                    title="Fetch Test 1",
                )
            )
            session.add(
                FetchDocument(
                    document_id="fetch-test-1",
                    status=FetchStatus.SUCCESS,
                    content_length=1000,
                    fetch_engine="trafilatura",
                )
            )
            session.commit()

        # Check status shows fetched document
        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        assert data["documents"]["by_status"]["fetched"] == 1

    def test_status_multiple_domains(self, cli_runner: CliRunner, tmp_status_project):
        """Verify status correctly aggregates documents by domain."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        domains = ["alpha.com", "beta.com", "gamma.com"]

        with managed_session() as session:
            doc_id = 0
            for domain in domains:
                count = domains.index(domain) + 1  # 1, 2, 3 documents per domain
                for i in range(count):
                    session.add(
                        MapDocument(
                            document_id=f"domain-test-{doc_id}",
                            source_url=f"https://{domain}/page{i}",
                            source_type="url",
                            discovery_method="sitemap",
                            status=MapStatus.SUCCESS,
                            title=f"{domain} Page {i}",
                        )
                    )
                    doc_id += 1
            session.commit()

        result = invoke_cli(cli_runner, status, ["--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        by_domain = data["documents"]["by_domain"]
        assert by_domain["alpha.com"] == 1
        assert by_domain["beta.com"] == 2
        assert by_domain["gamma.com"] == 3
        assert data["documents"]["total"] == 6
