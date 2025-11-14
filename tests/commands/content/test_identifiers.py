"""
Unit tests for identifier resolution in content commands.

Tests the common _identifiers.py module that handles:
- Full UUIDs
- Partial UUIDs (8+ characters)
- URLs
- File paths (with various strategies)
"""

from uuid import uuid4

from kurt.cli import main
from kurt.db.models import Document, IngestionStatus, SourceType


class TestIdentifierResolutionByURL:
    """Test identifier resolution by URL across all commands."""

    def test_get_by_url(self, isolated_cli_runner):
        """Test 'kurt content get <URL>' resolves to document."""
        runner, project_dir = isolated_cli_runner

        # Create test document with URL
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        test_url = "https://example.com/test-article"
        doc = Document(
            id=doc_id,
            source_url=test_url,
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Test Article by URL",
        )
        session.add(doc)
        session.commit()

        # Test get by URL
        result = runner.invoke(main, ["content", "get", test_url])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Test Article by URL" in result.output
        assert test_url in result.output

    def test_delete_by_url(self, isolated_cli_runner):
        """Test 'kurt content delete <URL>' resolves to document."""
        runner, project_dir = isolated_cli_runner

        # Create test document with URL
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        test_url = "https://example.com/delete-by-url"
        doc = Document(
            id=doc_id,
            source_url=test_url,
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Document to Delete by URL",
        )
        session.add(doc)
        session.commit()

        # Test delete by URL with confirmation
        result = runner.invoke(main, ["content", "delete", test_url], input="y\n")
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Deleted document" in result.output
        assert test_url in result.output

    def test_url_not_found(self, isolated_cli_runner):
        """Test error when URL doesn't match any document."""
        runner, project_dir = isolated_cli_runner

        # Try to get non-existent URL
        result = runner.invoke(main, ["content", "get", "https://example.com/nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestIdentifierResolutionByFilePath:
    """Test identifier resolution by file path across all commands."""

    def test_get_by_file_path_exact_match(self, isolated_cli_runner):
        """Test 'kurt content get <file_path>' with exact content_path match."""
        runner, project_dir = isolated_cli_runner

        # Create test document with content_path
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            source_url="https://example.com/article",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Document with File Path",
            content_path="example.com/article.md",
        )
        session.add(doc)
        session.commit()

        # Test get by file path (exact match)
        result = runner.invoke(main, ["content", "get", "example.com/article.md"])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Document with File Path" in result.output

    def test_get_by_file_path_with_sources_prefix(self, isolated_cli_runner):
        """Test 'kurt content get sources/<path>' strips prefix and matches."""
        runner, project_dir = isolated_cli_runner

        # Create test document (content_path WITHOUT sources/ prefix)
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            source_url="https://example.com/guide",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Guide with sources/ prefix test",
            content_path="example.com/guide.md",  # Stored without sources/
        )
        session.add(doc)
        session.commit()

        # Test get by file path WITH sources/ prefix
        result = runner.invoke(main, ["content", "get", "sources/example.com/guide.md"])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Guide with sources/ prefix test" in result.output

    def test_get_by_file_path_suffix_match(self, isolated_cli_runner):
        """Test file path resolution with suffix match (fallback strategy)."""
        runner, project_dir = isolated_cli_runner

        # Create test document
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            source_url="https://docs.example.com/tutorial/intro.html",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Tutorial Intro",
            content_path="docs.example.com/tutorial/intro.md",
        )
        session.add(doc)
        session.commit()

        # Test get by suffix
        result = runner.invoke(main, ["content", "get", "tutorial/intro.md"])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Tutorial Intro" in result.output

    def test_delete_by_file_path(self, isolated_cli_runner):
        """Test 'kurt content delete <file_path>' resolves to document."""
        runner, project_dir = isolated_cli_runner

        # Create test document with content_path
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            source_url="https://example.com/delete-by-path",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Delete by File Path",
            content_path="example.com/delete-by-path.md",
        )
        session.add(doc)
        session.commit()

        # Test delete by file path
        result = runner.invoke(
            main, ["content", "delete", "example.com/delete-by-path.md"], input="y\n"
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Deleted document" in result.output

    def test_file_path_not_found(self, isolated_cli_runner):
        """Test error when file path doesn't match any document."""
        runner, project_dir = isolated_cli_runner

        # Try to get non-existent file path
        result = runner.invoke(main, ["content", "get", "nonexistent/file.md"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_ambiguous_file_path(self, isolated_cli_runner):
        """Test error when file path matches multiple documents."""
        runner, project_dir = isolated_cli_runner

        # Create two documents with paths ending in same suffix
        from kurt.db.database import get_session

        session = get_session()
        doc1 = Document(
            id=uuid4(),
            source_url="https://site1.com/intro",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path="site1.com/docs/intro.md",
        )
        doc2 = Document(
            id=uuid4(),
            source_url="https://site2.com/intro",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path="site2.com/docs/intro.md",
        )
        session.add_all([doc1, doc2])
        session.commit()

        # Try to get by ambiguous suffix
        result = runner.invoke(main, ["content", "get", "docs/intro.md"])
        assert result.exit_code != 0
        assert "ambiguous" in result.output.lower()


class TestPartialUUIDInFilters:
    """Test partial UUID support in --ids filter option."""

    def test_index_with_partial_uuids_in_ids_filter(self, isolated_cli_runner):
        """Test 'kurt content index --ids <partial1>,<partial2>' works."""
        runner, project_dir = isolated_cli_runner

        # Create two test documents
        from kurt.db.database import get_session

        session = get_session()
        doc1_id = uuid4()
        doc2_id = uuid4()

        # Create content files
        sources_dir = project_dir / "sources"
        content1 = sources_dir / "doc1.md"
        content2 = sources_dir / "doc2.md"
        content1.write_text("# Document 1\n\nTest content 1.")
        content2.write_text("# Document 2\n\nTest content 2.")

        doc1 = Document(
            id=doc1_id,
            source_url="https://example.com/doc1",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Doc 1 for Partial UUID Test",
            content_path="doc1.md",
        )
        doc2 = Document(
            id=doc2_id,
            source_url="https://example.com/doc2",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Doc 2 for Partial UUID Test",
            content_path="doc2.md",
        )
        session.add_all([doc1, doc2])
        session.commit()

        # Test index with partial UUIDs (first 8 chars of each)
        partial1 = str(doc1_id)[:8]
        partial2 = str(doc2_id)[:8]
        result = runner.invoke(main, ["content", "index", "--ids", f"{partial1},{partial2}"])

        # Command should attempt to index both documents
        # (may fail due to missing LLM, but should resolve IDs correctly)
        assert result.exit_code == 0 or "OpenAI" in result.output or "litellm" in result.output
        # If it got past ID resolution, it found both docs
        if result.exit_code == 0:
            assert "2 document(s)" in result.output


class TestYesFlagReplacesForceFInYesFlagReplacesForce:
    """Test --yes/-y flag in commands that skip confirmations."""

    def test_delete_with_yes_flag(self, isolated_cli_runner):
        """Test 'kurt content delete <id> --yes' skips confirmation."""
        runner, project_dir = isolated_cli_runner

        # Create test document
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            source_url="https://example.com/yes-flag-test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Document for --yes test",
        )
        session.add(doc)
        session.commit()

        # Test delete with --yes (no input needed)
        result = runner.invoke(main, ["content", "delete", str(doc_id), "--yes"])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Deleted document" in result.output
        assert "Are you sure?" not in result.output  # No confirmation prompt

    def test_delete_with_y_shorthand(self, isolated_cli_runner):
        """Test 'kurt content delete <id> -y' shorthand works."""
        runner, project_dir = isolated_cli_runner

        # Create test document
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            source_url="https://example.com/y-shorthand-test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Document for -y test",
        )
        session.add(doc)
        session.commit()

        # Test delete with -y shorthand
        result = runner.invoke(main, ["content", "delete", str(doc_id), "-y"])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Deleted document" in result.output
        assert "Are you sure?" not in result.output

    def test_force_shows_deprecation_warning(self, isolated_cli_runner):
        """Test --force shows deprecation warning."""
        runner, project_dir = isolated_cli_runner

        # Create test document
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            source_url="https://example.com/force-deprecation",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Document for --force deprecation test",
        )
        session.add(doc)
        session.commit()

        # Test delete with deprecated --force flag
        result = runner.invoke(main, ["content", "delete", str(doc_id), "--force"])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "--force is deprecated" in result.output
        assert "--yes or -y instead" in result.output


class TestIndexCommandIdentifiers:
    """Test all identifier methods in index command."""

    def test_index_positional_partial_uuid(self, isolated_cli_runner):
        """Test 'kurt content index <partial_uuid>' works."""
        runner, project_dir = isolated_cli_runner

        # Create test document
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()

        # Create content file
        sources_dir = project_dir / "sources"
        content_file = sources_dir / "test-index.md"
        content_file.write_text("# Test Index\n\nContent for indexing.")

        doc = Document(
            id=doc_id,
            source_url="https://example.com/test-index",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Test Index Partial UUID",
            content_path="test-index.md",
        )
        session.add(doc)
        session.commit()

        # Test index with partial UUID (first 8 chars)
        partial_id = str(doc_id)[:8]
        result = runner.invoke(main, ["content", "index", partial_id])

        # Should resolve UUID and attempt indexing
        # (may fail due to missing LLM, but should resolve ID correctly)
        assert result.exit_code == 0 or "OpenAI" in result.output or "litellm" in result.output

    def test_index_positional_url(self, isolated_cli_runner):
        """Test 'kurt content index <URL>' works."""
        runner, project_dir = isolated_cli_runner

        # Create test document
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()
        test_url = "https://example.com/index-by-url"

        # Create content file
        sources_dir = project_dir / "sources"
        content_file = sources_dir / "index-url.md"
        content_file.write_text("# Index by URL\n\nContent.")

        doc = Document(
            id=doc_id,
            source_url=test_url,
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Index by URL Test",
            content_path="index-url.md",
        )
        session.add(doc)
        session.commit()

        # Test index with URL
        result = runner.invoke(main, ["content", "index", test_url])

        # Should resolve URL and attempt indexing
        assert result.exit_code == 0 or "OpenAI" in result.output or "litellm" in result.output

    def test_index_positional_file_path(self, isolated_cli_runner):
        """Test 'kurt content index <file_path>' works."""
        runner, project_dir = isolated_cli_runner

        # Create test document
        from kurt.db.database import get_session

        session = get_session()
        doc_id = uuid4()

        # Create content file
        sources_dir = project_dir / "sources"
        content_file = sources_dir / "example.com" / "index.md"
        content_file.parent.mkdir(parents=True, exist_ok=True)
        content_file.write_text("# Index by Path\n\nContent.")

        doc = Document(
            id=doc_id,
            source_url="https://example.com/index",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Index by File Path Test",
            content_path="example.com/index.md",
        )
        session.add(doc)
        session.commit()

        # Test index with file path (contains / so treated as path)
        result = runner.invoke(main, ["content", "index", "example.com/index.md"])

        # Should resolve path and attempt indexing
        assert result.exit_code == 0 or "OpenAI" in result.output or "litellm" in result.output


class TestFetchCommandFilters:
    """Test filter options in fetch command."""

    def test_fetch_with_include_pattern(self, isolated_cli_runner):
        """Test 'kurt content fetch --include <pattern>' works."""
        runner, project_dir = isolated_cli_runner

        # Create test documents
        from kurt.db.database import get_session

        session = get_session()
        doc1 = Document(
            id=uuid4(),
            source_url="https://docs.example.com/guide",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc2 = Document(
            id=uuid4(),
            source_url="https://blog.example.com/post",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add_all([doc1, doc2])
        session.commit()

        # Test fetch with include pattern (dry-run to avoid network calls)
        result = runner.invoke(
            main, ["content", "fetch", "--include", "*docs.example.com*", "--dry-run"]
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "DRY RUN" in result.output
        assert "1 document" in result.output  # Only docs.example.com matches

    def test_fetch_with_status_filter(self, isolated_cli_runner):
        """Test 'kurt content fetch --with-status <status>' works."""
        runner, project_dir = isolated_cli_runner

        # Create test documents with different statuses
        from kurt.db.database import get_session

        session = get_session()
        doc_not_fetched = Document(
            id=uuid4(),
            source_url="https://example.com/not-fetched",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc_fetched = Document(
            id=uuid4(),
            source_url="https://example.com/fetched",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add_all([doc_not_fetched, doc_fetched])
        session.commit()

        # Test fetch with status filter (dry-run)
        result = runner.invoke(
            main, ["content", "fetch", "--with-status", "NOT_FETCHED", "--dry-run"]
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "DRY RUN" in result.output
        assert "1 document" in result.output  # Only NOT_FETCHED doc

    def test_fetch_with_content_type_filter(self, isolated_cli_runner):
        """Test 'kurt content fetch --with-content-type <type>' works."""
        runner, project_dir = isolated_cli_runner

        # Create test documents with different content types
        from kurt.db.database import get_session
        from kurt.db.models import ContentType

        session = get_session()
        doc_tutorial = Document(
            id=uuid4(),
            source_url="https://example.com/tutorial",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
            content_type=ContentType.TUTORIAL,
        )
        doc_guide = Document(
            id=uuid4(),
            source_url="https://example.com/guide",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
            content_type=ContentType.GUIDE,
        )
        session.add_all([doc_tutorial, doc_guide])
        session.commit()

        # Test fetch with content type filter (dry-run)
        result = runner.invoke(
            main, ["content", "fetch", "--with-content-type", "tutorial", "--dry-run"]
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "DRY RUN" in result.output
        # Should only show tutorial document


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_partial_uuid_too_short(self, isolated_cli_runner):
        """Test error when partial UUID is less than 8 characters."""
        runner, project_dir = isolated_cli_runner

        # Try to get with too-short partial UUID (7 chars)
        # Note: get_document() accepts partial UUIDs but requires minimum 8 chars
        # A 7-char string will be treated as partial UUID and fail
        result = runner.invoke(main, ["content", "get", "550e840"])  # Only 7 chars
        assert result.exit_code != 0
        # Should fail with "too short" error message
        assert (
            "too short" in result.output.lower() and "minimum 8 characters" in result.output.lower()
        )

    def test_get_by_url_returns_successfully(self, isolated_cli_runner):
        """Test that URL resolution works and returns document successfully."""
        runner, project_dir = isolated_cli_runner

        # Create document with URL
        from kurt.db.database import get_session

        session = get_session()
        test_url = "https://example.com/url-resolution-test"
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            source_url=test_url,
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="URL Resolution Test Document",
        )
        session.add(doc)
        session.commit()

        # Test get by URL
        result = runner.invoke(main, ["content", "get", test_url])
        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Should show document details
        assert "Document Details" in result.output
        assert "URL Resolution Test Document" in result.output
        assert str(doc_id) in result.output

    def test_resolve_ids_to_uuids_utility(self, isolated_cli_runner):
        """Test the resolve_ids_to_uuids utility function with mixed identifiers."""
        runner, project_dir = isolated_cli_runner

        # Create test documents
        from kurt.db.database import get_session

        session = get_session()

        # Document 1: with URL
        doc1_id = uuid4()
        doc1 = Document(
            id=doc1_id,
            source_url="https://example.com/doc1",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Doc 1",
        )
        session.add(doc1)

        # Document 2: with file path
        sources_dir = project_dir / "sources"
        content_file = sources_dir / "example.com" / "doc2.md"
        content_file.parent.mkdir(parents=True, exist_ok=True)
        content_file.write_text("Content 2")

        doc2_id = uuid4()
        doc2 = Document(
            id=doc2_id,
            source_url="https://example.com/doc2",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Doc 2",
            content_path="example.com/doc2.md",
        )
        session.add(doc2)

        # Document 3: by partial UUID only
        doc3_id = uuid4()
        doc3 = Document(
            id=doc3_id,
            source_url="https://example.com/doc3",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            title="Doc 3",
        )
        session.add(doc3)
        session.commit()

        # Test resolve_ids_to_uuids with mixed identifiers
        from kurt.content.filtering import resolve_ids_to_uuids

        partial_uuid = str(doc3_id)[:8]
        mixed_ids = f"https://example.com/doc1,example.com/doc2.md,{partial_uuid}"

        resolved = resolve_ids_to_uuids(mixed_ids)

        assert len(resolved) == 3
        assert str(doc1_id) in resolved
        assert str(doc2_id) in resolved
        assert str(doc3_id) in resolved
