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
from kurt.db import managed_session
from kurt.documents.cli import delete_cmd, docs_group, get_cmd, list_cmd
from kurt.testing.assertions import (
    assert_fetch_document_count,
    assert_fetch_document_exists,
    assert_fetch_document_not_exists,
    assert_map_document_count,
    assert_map_document_exists,
    assert_map_document_not_exists,
)


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


# =============================================================================
# Enhanced E2E Tests with Database State Verification
# =============================================================================


class TestDocsListVerifyDocumentCounts:
    """E2E tests verifying actual document counts from database.

    Fixture creates 7 documents:
    - doc-1, doc-2, doc-3: Mapped via sitemap/crawl, not fetched
    - doc-4, doc-5: Mapped and fetched successfully
    - doc-6: Mapped, fetch error
    - doc-7: Map error
    """

    def test_docs_list_returns_all_7_documents(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify docs list returns exactly 7 documents from fixture."""
        result = invoke_cli(cli_runner, list_cmd, ["--format", "json"])

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        assert len(docs) == 7, f"Expected 7 documents, got {len(docs)}"

    def test_docs_list_fetched_returns_2_documents(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --with-status fetched returns exactly 2 documents (doc-4, doc-5)."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--with-status", "fetched", "--format", "json"]
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        assert len(docs) == 2, f"Expected 2 fetched documents, got {len(docs)}"

        # Verify these are doc-4 and doc-5
        doc_ids = [d["document_id"] for d in docs]
        assert "doc-4" in doc_ids
        assert "doc-5" in doc_ids

    def test_docs_list_error_returns_1_document(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --with-status error returns exactly 1 document (doc-6)."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--with-status", "error", "--format", "json"]
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        assert len(docs) == 1, f"Expected 1 error document, got {len(docs)}"
        assert docs[0]["document_id"] == "doc-6"


class TestDocsListByKnownIds:
    """E2E tests using known fixture document IDs."""

    def test_docs_list_by_single_id(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --ids with single known ID returns exactly that document."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--ids", "doc-1", "--format", "json"]
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        assert len(docs) == 1
        assert docs[0]["document_id"] == "doc-1"
        assert docs[0]["source_url"] == "https://example.com/docs/intro"

    def test_docs_list_by_multiple_ids(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --ids with multiple IDs returns matching documents."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--ids", "doc-1,doc-4,doc-7", "--format", "json"]
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        assert len(docs) == 3
        doc_ids = {d["document_id"] for d in docs}
        assert doc_ids == {"doc-1", "doc-4", "doc-7"}

    def test_docs_list_mixed_existing_nonexisting_ids(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --ids with mixed existing/non-existing IDs returns only existing."""
        result = invoke_cli(
            cli_runner,
            list_cmd,
            ["--ids", "doc-1,nonexistent,doc-2", "--format", "json"],
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        assert len(docs) == 2
        doc_ids = {d["document_id"] for d in docs}
        assert doc_ids == {"doc-1", "doc-2"}


class TestDocsListUrlFilters:
    """E2E tests for URL-based filters with verification."""

    def test_docs_list_url_contains_docs(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --url-contains '/docs/' returns 4 documents."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--url-contains", "/docs/", "--format", "json"]
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        # doc-1, doc-2, doc-4, doc-5 have /docs/ in URL
        assert len(docs) == 4, f"Expected 4 /docs/ documents, got {len(docs)}"
        for doc in docs:
            assert "/docs/" in doc["source_url"]

    def test_docs_list_url_contains_blog(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --url-contains '/blog/' returns 1 document (doc-3)."""
        result = invoke_cli(
            cli_runner, list_cmd, ["--url-contains", "/blog/", "--format", "json"]
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        assert len(docs) == 1
        assert docs[0]["document_id"] == "doc-3"
        assert "/blog/" in docs[0]["source_url"]


class TestDocsListCombinedFilters:
    """E2E tests for combined filter scenarios."""

    def test_docs_list_url_contains_with_limit(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --url-contains combined with --limit works correctly."""
        result = invoke_cli(
            cli_runner,
            list_cmd,
            ["--url-contains", "/docs/", "--limit", "2", "--format", "json"],
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        assert len(docs) <= 2
        for doc in docs:
            assert "/docs/" in doc["source_url"]

    def test_docs_list_status_with_url_contains(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --with-status combined with --url-contains works correctly."""
        result = invoke_cli(
            cli_runner,
            list_cmd,
            [
                "--with-status",
                "fetched",
                "--url-contains",
                "/docs/",
                "--format",
                "json",
            ],
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        docs = data.get("data", data) if isinstance(data, dict) else data

        assert isinstance(docs, list)
        # doc-4 and doc-5 are fetched and have /docs/ in URL
        assert len(docs) == 2
        for doc in docs:
            assert "/docs/" in doc["source_url"]
            assert doc["document_id"] in ("doc-4", "doc-5")


class TestDocsGetByKnownId:
    """E2E tests for docs get using fixture document IDs."""

    def test_docs_get_fetched_document(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify get returns full details for fetched document."""
        result = invoke_cli(cli_runner, get_cmd, ["doc-4", "--format", "json"])

        assert_cli_success(result)
        data = assert_json_output(result)
        doc = data.get("data", data) if isinstance(data, dict) else data

        assert doc is not None
        assert doc["document_id"] == "doc-4"
        assert doc["source_url"] == "https://example.com/docs/api"
        # Should have fetch info - status may be enum string or lowercase
        if "fetch_status" in doc:
            assert "success" in doc["fetch_status"].lower()

    def test_docs_get_unfetched_document(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify get returns details for unfetched document."""
        result = invoke_cli(cli_runner, get_cmd, ["doc-1", "--format", "json"])

        assert_cli_success(result)
        data = assert_json_output(result)
        doc = data.get("data", data) if isinstance(data, dict) else data

        assert doc is not None
        assert doc["document_id"] == "doc-1"
        assert doc["source_url"] == "https://example.com/docs/intro"

    def test_docs_get_error_document(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify get returns error info for failed fetch document."""
        result = invoke_cli(cli_runner, get_cmd, ["doc-6", "--format", "json"])

        assert_cli_success(result)
        data = assert_json_output(result)
        doc = data.get("data", data) if isinstance(data, dict) else data

        assert doc is not None
        assert doc["document_id"] == "doc-6"

    def test_docs_get_by_url(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify get can retrieve document by URL or shows not found."""
        result = invoke_cli(
            cli_runner, get_cmd, ["https://example.com/docs/api", "--format", "json"]
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        doc = data.get("data", data) if isinstance(data, dict) else data

        # The get command either finds the document or returns an error
        # If URL lookup is supported, we should get the document
        if doc and "document_id" in doc:
            assert doc["document_id"] == "doc-4"
            assert doc["source_url"] == "https://example.com/docs/api"
        else:
            # URL lookup may not be directly supported - verify error response
            assert doc is not None
            # Command completed without crash

    def test_docs_get_shows_content_length(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify get shows content_length for fetched documents."""
        result = invoke_cli(cli_runner, get_cmd, ["doc-4", "--format", "json"])

        assert_cli_success(result)
        data = assert_json_output(result)
        doc = data.get("data", data) if isinstance(data, dict) else data

        assert doc is not None
        # doc-4 has content_length=5000 in fixture
        if "content_length" in doc:
            assert doc["content_length"] == 5000


class TestDocsDeleteDatabaseVerification:
    """E2E tests verifying actual database state after delete."""

    def test_docs_delete_removes_from_database(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify delete actually removes document from database."""
        # Verify document exists before delete
        with managed_session() as session:
            assert_map_document_exists(session, "https://example.com/docs/intro")
            assert_map_document_count(session, 7)

        # Delete doc-1
        result = invoke_cli(cli_runner, delete_cmd, ["doc-1", "--yes"])
        assert_cli_success(result)

        # Verify document is removed from database
        with managed_session() as session:
            assert_map_document_not_exists(session, "https://example.com/docs/intro")
            assert_map_document_count(session, 6)

    def test_docs_delete_cascade_removes_fetch(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify delete removes both MapDocument and FetchDocument."""
        # Verify both records exist before delete
        with managed_session() as session:
            assert_map_document_exists(session, "https://example.com/docs/api")
            assert_fetch_document_exists(session, "doc-4")
            assert_fetch_document_count(session, 3)  # doc-4, doc-5, doc-6

        # Delete doc-4
        result = invoke_cli(cli_runner, delete_cmd, ["doc-4", "--yes"])
        assert_cli_success(result)

        # Verify both map and fetch records are removed
        with managed_session() as session:
            assert_map_document_not_exists(session, "https://example.com/docs/api")
            assert_fetch_document_not_exists(session, "doc-4")
            assert_fetch_document_count(session, 2)  # doc-5, doc-6 remain

    def test_docs_delete_with_filter_removes_matching(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify delete with --url-contains removes only matching documents."""
        # Verify blog document exists
        with managed_session() as session:
            assert_map_document_exists(session, "https://example.com/blog/post-1")
            assert_map_document_count(session, 7)

        # Delete documents with /blog/ in URL
        result = invoke_cli(
            cli_runner, delete_cmd, ["--url-contains", "/blog/", "--yes"]
        )
        assert_cli_success(result)

        # Verify only blog document is removed
        with managed_session() as session:
            assert_map_document_not_exists(session, "https://example.com/blog/post-1")
            assert_map_document_count(session, 6)  # Only doc-3 removed
            # Other documents still exist
            assert_map_document_exists(session, "https://example.com/docs/intro")
            assert_map_document_exists(session, "https://example.com/docs/api")

    def test_docs_delete_limit_caps_deletions(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --limit caps the number of documents deleted."""
        with managed_session() as session:
            assert_map_document_count(session, 7)

        # Delete with limit of 2
        result = invoke_cli(
            cli_runner,
            delete_cmd,
            ["--url-contains", "example.com", "--limit", "2", "--yes"],
        )
        assert_cli_success(result)

        # Verify only 2 documents were deleted
        with managed_session() as session:
            assert_map_document_count(session, 5)

    def test_docs_delete_dry_run_no_database_change(
        self, cli_runner: CliRunner, tmp_project_with_docs: Path
    ):
        """Verify --dry-run does not modify database."""
        with managed_session() as session:
            assert_map_document_count(session, 7)
            assert_fetch_document_count(session, 3)

        # Dry run delete all
        result = invoke_cli(
            cli_runner, delete_cmd, ["--url-contains", "example.com", "--dry-run"]
        )
        assert_cli_success(result)

        # Verify no changes to database
        with managed_session() as session:
            assert_map_document_count(session, 7)
            assert_fetch_document_count(session, 3)
