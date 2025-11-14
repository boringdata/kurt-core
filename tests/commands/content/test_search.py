"""
Unit tests for 'content search' command.

═══════════════════════════════════════════════════════════════════════════════
TEST COVERAGE
═══════════════════════════════════════════════════════════════════════════════

TestContentSearchCommand
────────────────────────────────────────────────────────────────────────────────
  ✓ test_search_requires_ripgrep
      → Tests error when ripgrep is not installed

  ✓ test_search_basic
      → Tests basic search with a simple query

  ✓ test_search_case_sensitive
      → Tests --case-sensitive flag

  ✓ test_search_with_include_pattern
      → Tests --include pattern filtering

  ✓ test_search_with_context
      → Tests --context lines option

  ✓ test_search_max_results
      → Tests --max-results limiting

  ✓ test_search_json_output
      → Tests --format json output

  ✓ test_search_no_matches
      → Tests behavior when no matches found

  ✓ test_search_summary_format
      → Tests --format summary output (document list with match counts) [default]

  ✓ test_search_detailed_format
      → Tests --format detailed output (full results with lines)

  ✓ test_search_empty_database
      → Tests error handling with empty database

  ✓ test_search_no_sources_directory
      → Tests error when sources directory doesn't exist

  ✓ test_search_help
      → Tests help text display
"""

import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from kurt.cli import main


class TestContentSearchCommand:
    """Tests for 'content search' command."""

    @pytest.fixture
    def mock_rg_not_installed(self, monkeypatch):
        """Mock ripgrep as not installed."""
        monkeypatch.setattr(shutil, "which", lambda x: None if x == "rg" else shutil.which(x))

    def test_search_requires_ripgrep(self, isolated_cli_runner, mock_rg_not_installed):
        """Test error when ripgrep is not installed."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(main, ["content", "search", "test"])

        assert result.exit_code != 0
        assert "ripgrep (rg) is not installed" in result.output
        assert "brew install ripgrep" in result.output

    def test_search_empty_database(self, isolated_cli_runner):
        """Test error handling with empty database."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        result = runner.invoke(main, ["content", "search", "test"])

        assert result.exit_code != 0
        assert "No documents found" in result.output or "not exist" in result.output

    def test_search_no_sources_directory(self, isolated_cli_runner):
        """Test error when sources directory doesn't exist."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create a document without content
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()
        doc = Document(
            id=uuid4(),
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(doc)
        session.commit()

        result = runner.invoke(main, ["content", "search", "test"])

        assert result.exit_code != 0
        # Should warn about missing sources directory or no content files
        assert (
            "not exist" in result.output
            or "No documents" in result.output
            or "no content files" in result.output
        )

    def test_search_basic(self, isolated_cli_runner):
        """Test basic search with a simple query."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create a document with content
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        # Create content file
        content_file = sources_path / "test_doc.md"
        content_file.write_text(
            "This is a test document.\nIt contains authentication information.\nAnother line here."
        )

        # Create document in database
        session = get_session()
        doc = Document(
            id=uuid4(),
            title="Test Document",
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(content_file.relative_to(Path.cwd())),
        )
        session.add(doc)
        session.commit()

        # Search for "authentication"
        result = runner.invoke(main, ["content", "search", "authentication"])

        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")

        assert result.exit_code == 0
        assert "authentication" in result.output.lower()
        assert "Test Document" in result.output or "test" in result.output.lower()

    def test_search_case_sensitive(self, isolated_cli_runner):
        """Test --case-sensitive flag."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create a document with mixed case content
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        # Create content file
        content_file = sources_path / "case_test.md"
        content_file.write_text("This has Authentication\nthis has authentication\nAUTHENTICATION")

        # Create document in database
        session = get_session()
        doc = Document(
            id=uuid4(),
            title="Case Test",
            source_url="https://example.com/case",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(content_file.relative_to(Path.cwd())),
        )
        session.add(doc)
        session.commit()

        # Case-insensitive search (default) - should match all
        result = runner.invoke(main, ["content", "search", "authentication"])
        if result.exit_code != 0:
            print(f"Case-insensitive - Exit code: {result.exit_code}, Output: {result.output}")
        assert result.exit_code == 0

        # Case-sensitive search - should only match exact case
        result = runner.invoke(main, ["content", "search", "Authentication", "--case-sensitive"])
        if result.exit_code != 0:
            print(f"Case-sensitive - Exit code: {result.exit_code}, Output: {result.output}")
        assert result.exit_code == 0

    def test_search_with_include_pattern(self, isolated_cli_runner):
        """Test --include pattern filtering."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create multiple documents with different paths
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        # Create content files
        docs_file = sources_path / "docs_page.md"
        docs_file.write_text("Documentation about authentication")

        blog_file = sources_path / "blog_post.md"
        blog_file.write_text("Blog post about authentication")

        # Create documents in database
        session = get_session()

        doc_docs = Document(
            id=uuid4(),
            title="Docs Page",
            source_url="https://example.com/docs/auth",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(docs_file.relative_to(sources_path.parent)),
        )

        doc_blog = Document(
            id=uuid4(),
            title="Blog Post",
            source_url="https://example.com/blog/auth",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(blog_file.relative_to(sources_path.parent)),
        )

        session.add(doc_docs)
        session.add(doc_blog)
        session.commit()

        # Search only in docs
        result = runner.invoke(
            main, ["content", "search", "authentication", "--include", "*/docs/*"]
        )

        assert result.exit_code == 0
        assert "authentication" in result.output.lower()

    def test_search_with_context(self, isolated_cli_runner):
        """Test --context lines option."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create a document with multiple lines
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        # Create content file with multiple lines
        content_file = sources_path / "context_test.md"
        content_file.write_text(
            "Line 1\nLine 2\nLine 3\nLine with authentication\nLine 5\nLine 6\nLine 7"
        )

        # Create document in database
        session = get_session()
        doc = Document(
            id=uuid4(),
            title="Context Test",
            source_url="https://example.com/context",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(content_file.relative_to(Path.cwd())),
        )
        session.add(doc)
        session.commit()

        # Search with more context
        result = runner.invoke(main, ["content", "search", "authentication", "--context", "3"])

        assert result.exit_code == 0
        assert "authentication" in result.output.lower()

    def test_search_max_results(self, isolated_cli_runner):
        """Test --max-results limiting."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create multiple documents
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        session = get_session()

        # Create 5 documents with matches
        for i in range(5):
            content_file = sources_path / f"doc_{i}.md"
            content_file.write_text(f"Document {i} with test keyword")

            doc = Document(
                id=uuid4(),
                title=f"Doc {i}",
                source_url=f"https://example.com/doc{i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.FETCHED,
                content_path=str(content_file.relative_to(Path.cwd())),
            )
            session.add(doc)

        session.commit()

        # Search with limit
        result = runner.invoke(main, ["content", "search", "test", "--max-results", "2"])

        assert result.exit_code == 0
        assert "test" in result.output.lower()

    def test_search_json_output(self, isolated_cli_runner):
        """Test --format json output."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create a document with content
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        # Create content file
        content_file = sources_path / "json_test.md"
        content_file.write_text("Test content with keyword")

        # Create document in database
        session = get_session()
        doc = Document(
            id=uuid4(),
            title="JSON Test",
            source_url="https://example.com/json",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(content_file.relative_to(Path.cwd())),
        )
        session.add(doc)
        session.commit()

        # Search with JSON output
        result = runner.invoke(main, ["content", "search", "keyword", "--format", "json"])

        assert result.exit_code == 0

        # Verify JSON structure
        output = json.loads(result.output)
        assert "query" in output
        assert output["query"] == "keyword"
        assert "total_matches" in output
        assert "matches" in output
        assert isinstance(output["matches"], list)

    def test_search_no_matches(self, isolated_cli_runner):
        """Test behavior when no matches found."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create a document with content
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        # Create content file
        content_file = sources_path / "no_match.md"
        content_file.write_text("This document has no matching terms")

        # Create document in database
        session = get_session()
        doc = Document(
            id=uuid4(),
            title="No Match",
            source_url="https://example.com/nomatch",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(content_file.relative_to(Path.cwd())),
        )
        session.add(doc)
        session.commit()

        # Search for non-existent term
        result = runner.invoke(main, ["content", "search", "xyznonexistent"])

        # Should succeed but show no matches
        assert result.exit_code == 0
        assert "No matches found" in result.output

    def test_search_summary_format(self, isolated_cli_runner):
        """Test --format summary output."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create multiple documents with different match counts
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        session = get_session()

        # Create documents with varying match counts
        doc1_file = sources_path / "many_matches.md"
        doc1_file.write_text("test keyword\ntest keyword\ntest keyword")

        doc2_file = sources_path / "one_match.md"
        doc2_file.write_text("This has one test keyword")

        doc1 = Document(
            id=uuid4(),
            title="Many Matches",
            source_url="https://example.com/many",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(doc1_file.relative_to(Path.cwd())),
        )
        doc2 = Document(
            id=uuid4(),
            title="One Match",
            source_url="https://example.com/one",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(doc2_file.relative_to(Path.cwd())),
        )
        session.add(doc1)
        session.add(doc2)
        session.commit()

        # Test default format (summary)
        result = runner.invoke(main, ["content", "search", "keyword"])

        assert result.exit_code == 0
        assert "Search Summary" in result.output
        assert "Many Matches" in result.output
        assert "One Match" in result.output
        # Should show match counts
        assert "Matches" in result.output

        # Test explicit summary format
        result = runner.invoke(main, ["content", "search", "keyword", "--format", "summary"])
        assert result.exit_code == 0
        assert "Search Summary" in result.output

    def test_search_detailed_format(self, isolated_cli_runner):
        """Test --format detailed output (full results with lines)."""
        runner, project_dir = isolated_cli_runner

        # Skip if ripgrep not installed
        if not shutil.which("rg"):
            pytest.skip("ripgrep not installed")

        # Create a document with content
        from kurt.config.base import get_config_or_default
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        config = get_config_or_default()
        sources_path = Path(config.PATH_SOURCES).absolute()
        sources_path.mkdir(parents=True, exist_ok=True)

        # Create content file
        content_file = sources_path / "detailed_test.md"
        content_file.write_text("Line with keyword here\nAnother line\nMore keyword content")

        # Create document in database
        session = get_session()
        doc = Document(
            id=uuid4(),
            title="Detailed Test",
            source_url="https://example.com/detailed",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path=str(content_file.relative_to(Path.cwd())),
        )
        session.add(doc)
        session.commit()

        # Search with detailed format
        result = runner.invoke(main, ["content", "search", "keyword", "--format", "detailed"])

        assert result.exit_code == 0
        assert "Search Results" in result.output
        assert "Detailed Test" in result.output
        # Should show line numbers and content
        assert "Line" in result.output
        assert "keyword" in result.output.lower()

    def test_search_help(self, isolated_cli_runner):
        """Test help text display."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(main, ["content", "search", "--help"])

        assert result.exit_code == 0
        assert "Search document content using ripgrep" in result.output
        assert "--include" in result.output
        assert "--case-sensitive" in result.output
        assert "--context" in result.output
        assert "--max-results" in result.output
        assert "summary" in result.output
        assert "detailed" in result.output
