"""Tests for fetch workflow CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.tools.fetch.cli import fetch_cmd


@pytest.fixture
def mock_dolt_db():
    """Create a mock DoltDB that returns empty results."""
    mock_db = MagicMock()
    mock_db.query.return_value = []
    mock_db.execute.return_value = 0
    return mock_db


@pytest.fixture
def mock_resolve_documents():
    """Mock resolve_documents to return empty list (no docs found)."""
    with patch("kurt.documents.resolve_documents") as mock:
        mock.return_value = []
        yield mock


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
        # Advanced filter options
        assert_output_contains(result, "--url-contains")
        assert_output_contains(result, "--file-ext")
        assert_output_contains(result, "--source-type")
        assert_output_contains(result, "--exclude")
        assert_output_contains(result, "--has-content")
        assert_output_contains(result, "--min-content-length")
        # Input options
        assert_output_contains(result, "--url")
        assert_output_contains(result, "--urls")
        assert_output_contains(result, "--file")
        assert_output_contains(result, "--files")
        assert_output_contains(result, "--engine")
        assert_output_contains(result, "--batch-size")
        assert_output_contains(result, "--refetch")

    def test_fetch_no_docs_message(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch shows message when no documents found."""
        result = invoke_cli(cli_runner, fetch_cmd, [])
        assert_cli_success(result)
        assert_output_contains(result, "No documents")

    def test_fetch_with_identifier(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch with identifier argument."""
        result = invoke_cli(cli_runner, fetch_cmd, ["some-id"])
        assert_cli_success(result)

    def test_fetch_with_limit(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --limit option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--limit", "10"])
        assert_cli_success(result)

    def test_fetch_with_include_pattern(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --include option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--include", "*.md"])
        assert_cli_success(result)

    def test_fetch_with_status_filter(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --with-status option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--with-status", "NOT_FETCHED"])
        assert_cli_success(result)

    def test_fetch_with_dry_run(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --dry-run option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--dry-run"])
        assert_cli_success(result)

    def test_fetch_with_json_format(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --format json option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--format", "json"])
        assert_cli_success(result)

    def test_fetch_with_background(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --background option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--background"])
        assert_cli_success(result)

    def test_fetch_with_priority(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --priority option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--priority", "5"])
        assert_cli_success(result)

    def test_fetch_combined_options(self, cli_runner: CliRunner, mock_resolve_documents):
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

    # Advanced filter options tests
    def test_fetch_with_url_contains(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --url-contains option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--url-contains", "/docs/"])
        assert_cli_success(result)

    def test_fetch_with_file_ext(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --file-ext option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--file-ext", "md"])
        assert_cli_success(result)

    def test_fetch_with_source_type(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --source-type option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--source-type", "url"])
        assert_cli_success(result)

    def test_fetch_with_exclude(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --exclude option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--exclude", "*internal*"])
        assert_cli_success(result)

    def test_fetch_with_has_content(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --has-content option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--has-content"])
        assert_cli_success(result)

    def test_fetch_with_no_content(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --no-content option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--no-content"])
        assert_cli_success(result)

    def test_fetch_with_min_content_length(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --min-content-length option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--min-content-length", "100"])
        assert_cli_success(result)

    # Input options tests
    def test_fetch_with_url_singular(self, cli_runner: CliRunner, mock_dolt_db):
        """Test fetch --url (singular) option auto-creates document."""
        with patch("kurt.db.documents.get_dolt_db") as mock_get:
            mock_get.return_value = mock_dolt_db
            with patch("kurt.documents.resolve_documents") as mock_resolve:
                mock_resolve.return_value = []
                result = invoke_cli(
                    cli_runner,
                    fetch_cmd,
                    ["--url", "https://example.com/article", "--dry-run"],
                )
                assert_cli_success(result)

    def test_fetch_with_urls(self, cli_runner: CliRunner, mock_dolt_db):
        """Test fetch --urls option auto-creates documents."""
        with patch("kurt.db.documents.get_dolt_db") as mock_get:
            mock_get.return_value = mock_dolt_db
            with patch("kurt.documents.resolve_documents") as mock_resolve:
                mock_resolve.return_value = []
                result = invoke_cli(
                    cli_runner,
                    fetch_cmd,
                    ["--urls", "https://example.com/article,https://example.com/other", "--dry-run"],
                )
                assert_cli_success(result)

    def test_fetch_with_file_singular(self, cli_runner: CliRunner, mock_dolt_db, tmp_path):
        """Test fetch --file (singular) option auto-creates document."""
        # Create temp file
        file1 = tmp_path / "doc1.md"
        file1.write_text("# Doc 1")

        with patch("kurt.db.documents.get_dolt_db") as mock_get:
            mock_get.return_value = mock_dolt_db
            with patch("kurt.documents.resolve_documents") as mock_resolve:
                mock_resolve.return_value = []
                result = invoke_cli(
                    cli_runner,
                    fetch_cmd,
                    ["--file", str(file1), "--dry-run"],
                )
                assert_cli_success(result)

    def test_fetch_with_files(self, cli_runner: CliRunner, mock_dolt_db, tmp_path):
        """Test fetch --files option auto-creates documents."""
        # Create temp files
        file1 = tmp_path / "doc1.md"
        file2 = tmp_path / "doc2.md"
        file1.write_text("# Doc 1")
        file2.write_text("# Doc 2")

        with patch("kurt.db.documents.get_dolt_db") as mock_get:
            mock_get.return_value = mock_dolt_db
            with patch("kurt.documents.resolve_documents") as mock_resolve:
                mock_resolve.return_value = []
                result = invoke_cli(
                    cli_runner,
                    fetch_cmd,
                    ["--files", f"{file1},{file2}", "--dry-run"],
                )
                assert_cli_success(result)

    def test_fetch_with_engine(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --engine option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--engine", "trafilatura", "--dry-run"])
        assert_cli_success(result)

    def test_fetch_with_engine_firecrawl(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --engine firecrawl option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--engine", "firecrawl", "--dry-run"])
        assert_cli_success(result)

    def test_fetch_with_refetch(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch --refetch option."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--refetch", "--dry-run"])
        assert_cli_success(result)

    def test_fetch_combined_advanced_options(self, cli_runner: CliRunner, mock_resolve_documents):
        """Test fetch with multiple advanced options combined."""
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            [
                "--url-contains",
                "/docs/",
                "--file-ext",
                "html",
                "--source-type",
                "url",
                "--exclude",
                "*internal*",
                "--limit",
                "10",
                "--dry-run",
            ],
        )
        assert_cli_success(result)
