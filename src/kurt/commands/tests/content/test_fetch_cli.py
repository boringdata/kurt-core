"""
Tests for 'content fetch' command.

These tests validate CLI argument handling, document filtering, and user interaction.
Tests mock the pipeline execution but use real code for everything else.

MOCKING STRATEGY:
- Mock run_pipeline_simple (the pipeline executor) - tested separately in model tests
- Use real code for: CLI parsing, document filtering, database operations
- Use tmp_project fixture for isolated test environment

NOTE: Status is now derived from staging tables (landing_fetch, staging_section_extractions).
Tests use _mark_document_as_fetched() helper to simulate fetched status.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from kurt.cli import main
from kurt.db.database import get_session
from kurt.db.models import Document, SourceType
from tests.helpers.status_helpers import (
    get_doc_status as _get_doc_status,
)
from tests.helpers.status_helpers import (
    mark_document_as_fetched as _mark_document_as_fetched,
)


@pytest.fixture
def mock_pipeline():
    """Mock the pipeline execution to avoid full pipeline runs in CLI tests."""
    with patch("kurt.workflows.cli_helpers.run_pipeline_simple") as mock_run:
        # Default successful result
        mock_run.return_value = {
            "landing.fetch": {
                "documents_fetched": 1,
                "documents_failed": 0,
                "rows_written": 1,
            },
            "errors": {},
        }
        yield mock_run


@pytest.fixture
def mock_pipeline_with_document_update():
    """Mock pipeline that also updates document status (simulates real behavior).

    Creates landing_fetch records to simulate successful fetch (status is now derived
    from staging tables, not stored on Document model).
    """

    def pipeline_side_effect(*args, **kwargs):
        # Get document IDs from the filters
        filters = kwargs.get("filters")
        doc_count = 0
        if filters and filters.ids:
            from uuid import UUID

            from kurt.db.database import get_session
            from kurt.db.models import Document

            session = get_session()
            for doc_id in filters.ids.split(","):
                try:
                    # Convert string to UUID for proper lookup
                    doc = session.get(Document, UUID(doc_id))
                    if doc:
                        _mark_document_as_fetched(str(doc.id), session)
                        doc_count += 1
                except (ValueError, TypeError):
                    pass

        return {
            "landing.fetch": {
                "documents_fetched": doc_count,
                "documents_failed": 0,
                "rows_written": doc_count,
            },
            "errors": {},
        }

    with patch("kurt.workflows.cli_helpers.run_pipeline_simple") as mock_run:
        mock_run.side_effect = pipeline_side_effect
        yield mock_run


class TestFetchCLIBasics:
    """Tests for basic fetch CLI functionality."""

    def test_fetch_requires_filter(self, isolated_cli_runner):
        """Test that fetch requires at least one filter."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(main, ["content", "fetch", "--yes"])

        # Should show help or error about needing filters
        assert "filter" in result.output.lower() or result.exit_code != 0

    def test_fetch_with_url_creates_document(
        self, isolated_cli_runner, mock_pipeline_with_document_update
    ):
        """Test fetch with URL auto-creates document if not exists."""
        runner, project_dir = isolated_cli_runner

        # Run fetch with URL that doesn't exist yet
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "https://example.com/new-page",
                "--skip-index",
                "--yes",
            ],
        )

        # Check command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify document was created
        from sqlmodel import select

        session = get_session()
        stmt = select(Document).where(Document.source_url == "https://example.com/new-page")
        doc = session.exec(stmt).first()
        assert doc is not None, "Document should be auto-created for new URL"

    def test_fetch_dry_run_no_execution(self, isolated_cli_runner, mock_pipeline):
        """Test that --dry-run doesn't execute pipeline."""
        runner, project_dir = isolated_cli_runner

        # Create a test document (status is NOT_FETCHED by default - no landing_fetch record)
        session = get_session()
        test_doc = Document(
            id=uuid4(),
            source_url="https://example.com/test",
            source_type=SourceType.URL,
        )
        session.add(test_doc)
        session.commit()

        # Run fetch with --dry-run
        result = runner.invoke(
            main, ["content", "fetch", "--urls", "https://example.com/test", "--dry-run"]
        )

        # Check command succeeded
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Preview only" in result.output

        # Verify pipeline was NOT called
        assert not mock_pipeline.called, "Pipeline should not be called in dry-run mode"

        # Verify document status was NOT updated (still NOT_FETCHED - no landing_fetch record)
        assert _get_doc_status(test_doc.id) == "NOT_FETCHED"


class TestFetchFiltering:
    """Tests for fetch document filtering options."""

    def test_fetch_with_include_pattern(
        self, isolated_cli_runner, mock_pipeline_with_document_update
    ):
        """Test fetch with --include pattern filters documents correctly."""
        runner, project_dir = isolated_cli_runner

        session = get_session()

        # Create documents - one matching, one not (status is NOT_FETCHED by default)
        doc_match = Document(
            id=uuid4(),
            source_url="https://example.com/docs/tutorial",
            source_type=SourceType.URL,
        )
        doc_no_match = Document(
            id=uuid4(),
            source_url="https://example.com/api/reference",
            source_type=SourceType.URL,
        )
        session.add_all([doc_match, doc_no_match])
        session.commit()

        # Run fetch with pattern
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--include",
                "*/docs/*",
                "--skip-index",
                "--yes",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify only matching document was fetched (status derived from staging tables)
        assert _get_doc_status(doc_match.id) == "FETCHED"
        assert _get_doc_status(doc_no_match.id) == "NOT_FETCHED"

    def test_fetch_with_ids_filter(self, isolated_cli_runner, mock_pipeline_with_document_update):
        """Test fetch with --ids option."""
        runner, project_dir = isolated_cli_runner

        session = get_session()

        # Create test documents (status is NOT_FETCHED by default)
        doc1 = Document(
            id=uuid4(),
            source_url="https://example.com/page1",
            source_type=SourceType.URL,
        )
        doc2 = Document(
            id=uuid4(),
            source_url="https://example.com/page2",
            source_type=SourceType.URL,
        )
        doc3 = Document(
            id=uuid4(),
            source_url="https://example.com/page3",
            source_type=SourceType.URL,
        )
        session.add_all([doc1, doc2, doc3])
        session.commit()

        # Run fetch with specific IDs
        ids_str = f"{doc1.id},{doc2.id}"
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--ids",
                ids_str,
                "--skip-index",
                "--yes",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify only specified documents were fetched (status derived from staging tables)
        assert _get_doc_status(doc1.id) == "FETCHED"
        assert _get_doc_status(doc2.id) == "FETCHED"
        assert _get_doc_status(doc3.id) == "NOT_FETCHED"

    def test_fetch_with_exclude_pattern(
        self, isolated_cli_runner, mock_pipeline_with_document_update
    ):
        """Test fetch with --exclude refinement option."""
        runner, project_dir = isolated_cli_runner

        session = get_session()

        # Create test documents (status is NOT_FETCHED by default)
        doc_included = Document(
            id=uuid4(),
            source_url="https://example.com/docs/tutorial",
            source_type=SourceType.URL,
        )
        doc_excluded = Document(
            id=uuid4(),
            source_url="https://example.com/docs/api/reference",
            source_type=SourceType.URL,
        )
        doc_included2 = Document(
            id=uuid4(),
            source_url="https://example.com/docs/guide",
            source_type=SourceType.URL,
        )
        session.add_all([doc_included, doc_excluded, doc_included2])
        session.commit()

        # Run fetch with include and exclude patterns
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--include",
                "*/docs/*",
                "--exclude",
                "*/api/*",
                "--skip-index",
                "--yes",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify only non-excluded documents were fetched (status derived from staging tables)
        assert _get_doc_status(doc_included.id) == "FETCHED"
        assert _get_doc_status(doc_excluded.id) == "NOT_FETCHED"
        assert _get_doc_status(doc_included2.id) == "FETCHED"

    def test_fetch_with_limit(self, isolated_cli_runner, mock_pipeline_with_document_update):
        """Test fetch with --limit option."""
        runner, project_dir = isolated_cli_runner

        session = get_session()

        # Create multiple test documents (status is NOT_FETCHED by default)
        docs = []
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/page{i}",
                source_type=SourceType.URL,
            )
            docs.append(doc)
            session.add(doc)
        session.commit()

        # Run fetch with limit=2
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--with-status",
                "NOT_FETCHED",
                "--limit",
                "2",
                "--skip-index",
                "--yes",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify only 2 documents were fetched (status derived from staging tables)
        fetched_count = sum(1 for doc in docs if _get_doc_status(doc.id) == "FETCHED")
        assert fetched_count == 2


class TestFetchConfirmation:
    """Tests for fetch confirmation and safety guardrails."""

    def test_fetch_concurrency_warning_over_20(self, isolated_cli_runner, mock_pipeline):
        """Test warning when concurrency >20 without --yes."""
        runner, project_dir = isolated_cli_runner

        session = get_session()
        doc = Document(
            id=uuid4(),
            source_url="https://example.com/test",
            source_type=SourceType.URL,
        )
        session.add(doc)
        session.commit()

        # Run fetch with high concurrency and decline
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--urls",
                "https://example.com/test",
                "--concurrency",
                "25",
                "--skip-index",
            ],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "High concurrency" in result.output or "rate limit" in result.output
        assert "Aborted" in result.output

        # Pipeline should not be called
        assert not mock_pipeline.called

    def test_fetch_concurrency_bypassed_with_yes(
        self, isolated_cli_runner, mock_pipeline_with_document_update
    ):
        """Test --yes bypasses concurrency warning."""
        runner, project_dir = isolated_cli_runner

        session = get_session()
        doc = Document(
            id=uuid4(),
            source_url="https://example.com/test",
            source_type=SourceType.URL,
        )
        session.add(doc)
        session.commit()

        # Run fetch with high concurrency and --yes
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--urls",
                "https://example.com/test",
                "--concurrency",
                "25",
                "--yes",
                "--skip-index",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Continue anyway?" not in result.output

        # Document should be fetched (status derived from staging tables)
        assert _get_doc_status(doc.id) == "FETCHED"


class TestFetchRefetch:
    """Tests for --refetch flag behavior."""

    def test_fetch_skips_fetched_by_default(self, isolated_cli_runner, mock_pipeline):
        """Test that already FETCHED documents are skipped by default."""
        runner, project_dir = isolated_cli_runner

        session = get_session()
        # Create document and mark as FETCHED via landing_fetch table
        doc_fetched = Document(
            id=uuid4(),
            source_url="https://example.com/fetched",
            source_type=SourceType.URL,
            content_path="example.com/fetched.md",
        )
        session.add(doc_fetched)
        session.commit()
        _mark_document_as_fetched(str(doc_fetched.id), session)

        # Run fetch without --refetch
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--urls",
                "https://example.com/fetched",
                "--skip-index",
                "--yes",
            ],
        )

        # Should show message about documents being already fetched
        assert "FETCHED" in result.output or "refetch" in result.output.lower()

        # Pipeline should not be called (no documents to fetch)
        assert not mock_pipeline.called

    def test_fetch_with_refetch_includes_fetched(
        self, isolated_cli_runner, mock_pipeline_with_document_update
    ):
        """Test --refetch includes already FETCHED documents."""
        runner, project_dir = isolated_cli_runner

        session = get_session()
        # Create document and mark as FETCHED via landing_fetch table
        doc_fetched = Document(
            id=uuid4(),
            source_url="https://example.com/fetched",
            source_type=SourceType.URL,
            content_path="example.com/fetched.md",
        )
        session.add(doc_fetched)
        session.commit()
        _mark_document_as_fetched(str(doc_fetched.id), session)

        # Run fetch with --refetch
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--urls",
                "https://example.com/fetched",
                "--refetch",
                "--skip-index",
                "--yes",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Document should still be FETCHED (refetched successfully)
        assert _get_doc_status(doc_fetched.id) == "FETCHED"


class TestFetchOutputFormat:
    """Tests for fetch output format options."""

    def test_fetch_json_output_format(self, isolated_cli_runner, mock_pipeline):
        """Validate JSON output structure."""
        runner, project_dir = isolated_cli_runner

        import json

        session = get_session()
        doc1 = Document(
            id=uuid4(),
            source_url="https://example.com/page1",
            source_type=SourceType.URL,
        )
        doc2 = Document(
            id=uuid4(),
            source_url="https://example.com/page2",
            source_type=SourceType.URL,
        )
        session.add_all([doc1, doc2])
        session.commit()

        # Run fetch with --format json and decline
        result = runner.invoke(
            main,
            ["content", "fetch", "--with-status", "NOT_FETCHED", "--format", "json"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "total" in result.output
        assert "documents" in result.output

        # Extract and parse JSON
        lines = result.output.split("\n")
        json_lines = []
        brace_count = 0
        in_json = False

        for line in lines:
            if "{" in line and not in_json:
                in_json = True
            if in_json:
                json_lines.append(line)
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0:
                    break

        if json_lines:
            json_output = "\n".join(json_lines)
            parsed = json.loads(json_output)
            assert "total" in parsed
            assert "documents" in parsed
            assert parsed["total"] == 2
            assert len(parsed["documents"]) == 2


class TestFetchLocalFiles:
    """Tests for fetch command with local file ingestion."""

    def test_fetch_with_file_option(self, isolated_cli_runner):
        """Test fetch with local file path."""
        runner, project_dir = isolated_cli_runner

        from kurt.config import load_config

        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create a test markdown file
        test_file = sources_dir / "test_article.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Test Article\n\nThis is test content.")

        # Run fetch with file path
        result = runner.invoke(main, ["content", "fetch", str(test_file), "--skip-index"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify document was created
        from sqlmodel import select

        session = get_session()
        stmt = select(Document).where(Document.content_path == "test_article.md")
        doc = session.exec(stmt).first()

        assert doc is not None, "Document should be created"
        assert doc.title == "Test Article"
        assert doc.source_type == SourceType.FILE_UPLOAD
        # Status derived from staging tables (local files are marked FETCHED via landing_fetch)
        assert _get_doc_status(doc.id) == "FETCHED"

    def test_fetch_with_files_option(self, isolated_cli_runner):
        """Test fetch with --files option for multiple local files."""
        runner, project_dir = isolated_cli_runner

        from kurt.config import load_config

        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create multiple test files
        test_file1 = sources_dir / "article1.md"
        test_file2 = sources_dir / "article2.md"

        test_file1.parent.mkdir(parents=True, exist_ok=True)
        test_file1.write_text("# First Article\n\nContent for first article.")
        test_file2.write_text("# Second Article\n\nContent for second article.")

        # Run fetch with --files
        files_str = f"{test_file1},{test_file2}"
        result = runner.invoke(main, ["content", "fetch", "--files", files_str, "--skip-index"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify both documents were created
        from sqlmodel import select

        session = get_session()

        stmt1 = select(Document).where(Document.content_path == "article1.md")
        doc1 = session.exec(stmt1).first()

        stmt2 = select(Document).where(Document.content_path == "article2.md")
        doc2 = session.exec(stmt2).first()

        assert doc1 is not None
        assert doc2 is not None
        assert doc1.title == "First Article"
        assert doc2.title == "Second Article"

    def test_fetch_file_outside_sources_directory(self, isolated_cli_runner):
        """Test fetch copies files outside sources/ to sources/local/."""
        runner, project_dir = isolated_cli_runner

        import tempfile
        from pathlib import Path

        from kurt.config import load_config

        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create a temporary file OUTSIDE sources directory
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
            tmp.write("# External Article\n\nThis file is outside sources directory.")
            tmp_path = Path(tmp.name)

        try:
            result = runner.invoke(main, ["content", "fetch", str(tmp_path), "--skip-index"])

            assert result.exit_code == 0, f"Command failed: {result.output}"
            assert "Copied" in result.output
            assert "sources/local/" in result.output

            # Verify file was copied
            expected_copy = sources_dir / "local" / tmp_path.name
            assert expected_copy.exists()

            # Verify document was created
            from sqlmodel import select

            session = get_session()
            expected_content_path = f"local/{tmp_path.name}"
            stmt = select(Document).where(Document.content_path == expected_content_path)
            doc = session.exec(stmt).first()

            assert doc is not None
            assert doc.title == "External Article"
            assert doc.source_type == SourceType.FILE_UPLOAD
            # Status derived from staging tables
            assert _get_doc_status(doc.id) == "FETCHED"

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_fetch_file_nonexistent(self, isolated_cli_runner):
        """Test fetch with non-existent file returns error."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(
            main, ["content", "fetch", "/tmp/nonexistent_file_xyz123.md", "--skip-index"]
        )

        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_fetch_file_title_from_filename(self, isolated_cli_runner):
        """Test fetch extracts title from filename when no markdown heading."""
        runner, project_dir = isolated_cli_runner

        from kurt.config import load_config

        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create a test file WITHOUT markdown heading
        test_file = sources_dir / "my-article-title.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Just plain text without a heading.")

        result = runner.invoke(main, ["content", "fetch", str(test_file), "--skip-index"])

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify title was extracted from filename
        from sqlmodel import select

        session = get_session()
        stmt = select(Document).where(Document.content_path == "my-article-title.md")
        doc = session.exec(stmt).first()

        assert doc is not None
        # Title should be filename-based
        assert "article" in doc.title.lower() or "my-article-title" in doc.title.lower()
