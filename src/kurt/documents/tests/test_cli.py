"""Tests for documents CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_json_output,
    assert_output_contains,
    invoke_cli,
)
from kurt.documents.cli import content_group


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

    def test_get_partial_id_match(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test get command finds document by partial ID."""
        # doc-1 exists in tmp_project_with_docs
        result = invoke_cli(cli_runner, content_group, ["get", "doc-1", "--format", "json"])
        assert_cli_success(result)
        data = assert_json_output(result)
        assert data.get("document_id") == "doc-1"

        # Test partial ID (just "oc-1" should still match "doc-1")
        result = invoke_cli(cli_runner, content_group, ["get", "oc-1", "--format", "json"])
        assert_cli_success(result)
        data = assert_json_output(result)
        assert "doc-1" in data.get("document_id", "")

    def test_get_by_url(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test get command finds document by URL."""
        # doc-1 has source_url https://example.com/docs/intro
        result = invoke_cli(
            cli_runner,
            content_group,
            ["get", "https://example.com/docs/intro", "--format", "json"],
        )
        assert_cli_success(result)
        data = assert_json_output(result)
        assert data.get("source_url") == "https://example.com/docs/intro"


class TestResolveDocumentsUrlAutoCreate:
    """Tests for resolve_documents URL auto-creation."""

    def test_resolve_url_identifier_creates_document(self, tmp_database):
        """Test that passing a URL as identifier auto-creates MapDocument."""
        from kurt.db import managed_session
        from kurt.documents import resolve_documents
        from kurt.workflows.map.models import MapDocument

        test_url = "https://example.com/test-auto-create"

        # Before: document doesn't exist
        with managed_session() as session:
            existing = session.query(MapDocument).filter(MapDocument.source_url == test_url).first()
            assert existing is None

        # Call resolve_documents with URL as identifier
        docs = resolve_documents(identifier=test_url)

        # After: document was auto-created and returned
        assert len(docs) == 1
        assert docs[0]["source_url"] == test_url

        # Verify it was persisted
        with managed_session() as session:
            created = session.query(MapDocument).filter(MapDocument.source_url == test_url).first()
            assert created is not None
            assert created.source_type == "url"
            assert created.discovery_method == "cli"

    def test_resolve_url_identifier_uses_existing_document(self, tmp_project_with_docs):
        """Test that passing a URL that already exists returns existing document."""
        from kurt.documents import resolve_documents

        # doc-1 has source_url https://example.com/docs/intro
        existing_url = "https://example.com/docs/intro"

        docs = resolve_documents(identifier=existing_url)

        assert len(docs) == 1
        assert docs[0]["document_id"] == "doc-1"  # Uses existing ID, not hash

    def test_resolve_non_url_identifier_uses_id_filter(self, tmp_project_with_docs):
        """Test that non-URL identifier is treated as document ID."""
        from kurt.documents import resolve_documents

        docs = resolve_documents(identifier="doc-1")

        assert len(docs) == 1
        assert docs[0]["document_id"] == "doc-1"


class TestSourceUrlUniqueConstraint:
    """Tests for source_url unique constraint on map_documents."""

    def test_unique_constraint_prevents_duplicates(self, tmp_database):
        """Test that new documents with duplicate URLs are rejected."""
        import pytest
        from sqlalchemy.exc import IntegrityError

        from kurt.db import managed_session
        from kurt.workflows.map.models import MapDocument, MapStatus

        test_url = "https://example.com/unique-test"

        # First insert should succeed
        with managed_session() as session:
            doc1 = MapDocument(
                document_id="unique-doc-1",
                source_url=test_url,
                source_type="url",
                status=MapStatus.SUCCESS,
            )
            session.add(doc1)
            session.commit()

        # Second insert with same URL should fail
        with pytest.raises(IntegrityError):
            with managed_session() as session:
                doc2 = MapDocument(
                    document_id="unique-doc-2",
                    source_url=test_url,
                    source_type="url",
                    status=MapStatus.SUCCESS,
                )
                session.add(doc2)
                session.commit()
