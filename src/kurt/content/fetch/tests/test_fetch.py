"""
Tests for 'fetch' command (root-level) with mocked HTTP responses.

These tests use mocked trafilatura responses to avoid network calls.
NOTE: fetch command moved from 'content fetch' to root level 'fetch'
"""

from unittest.mock import patch

from kurt.cli import main
from kurt.db.models import Document, IngestionStatus, SourceType


class TestFetchWithMockedResponses:
    """Tests for fetch command with mocked HTTP responses."""

    def test_fetch_with_trafilatura_mocked(self, isolated_cli_runner):
        """Test fetch command with mocked trafilatura responses."""
        runner, project_dir = isolated_cli_runner

        # First, create a test document to fetch
        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()
        test_doc = Document(
            id=uuid4(),
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(test_doc)
        session.commit()

        # Mock trafilatura.fetch_url and trafilatura.extract
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    # Setup mocks
                    mock_fetch.return_value = "<html><body>Test content</body></html>"
                    mock_extract.return_value = "Test content extracted"
                    mock_metadata.return_value = None  # Metadata can be None

                    # Run fetch command (content fetch)
                    result = runner.invoke(
                        main,
                        [
                            "content",
                            "fetch",
                            "--urls",
                            "https://example.com/test",
                            "--engine",
                            "trafilatura",
                            "--skip-index",  # Skip LLM to keep test fast
                        ],
                    )

                    # Check command succeeded
                    assert result.exit_code == 0, f"Command failed: {result.output}"
                    assert "Fetching" in result.output or "Fetched" in result.output

                    # Verify mocks were called
                    assert mock_fetch.called
                    assert mock_extract.called

        # Verify document status was updated
        session.refresh(test_doc)
        assert test_doc.ingestion_status == IngestionStatus.FETCHED

    def test_fetch_dry_run_no_network_calls(self, isolated_cli_runner):
        """Test that --dry-run makes no network calls."""
        runner, project_dir = isolated_cli_runner

        # Create a test document
        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()
        test_doc = Document(
            id=uuid4(),
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(test_doc)
        session.commit()

        # Mock trafilatura to ensure it's NOT called
        with patch("trafilatura.fetch_url") as mock_fetch:
            # Run fetch with --dry-run
            result = runner.invoke(
                main, ["content", "fetch", "--urls", "https://example.com/test", "--dry-run"]
            )

            # Check command succeeded
            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            assert "Preview only" in result.output

            # Verify NO network calls were made
            assert not mock_fetch.called, "fetch_url should not be called in dry-run mode"

        # Verify document status was NOT updated
        session.refresh(test_doc)
        assert test_doc.ingestion_status == IngestionStatus.NOT_FETCHED

    def test_fetch_with_include_pattern_mocked(self, isolated_cli_runner):
        """Test fetch with --include pattern and mocked responses."""
        runner, project_dir = isolated_cli_runner

        # Create multiple test documents
        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Document that matches pattern
        doc_match = Document(
            id=uuid4(),
            source_url="https://example.com/docs/tutorial",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )

        # Document that doesn't match pattern
        doc_no_match = Document(
            id=uuid4(),
            source_url="https://example.com/api/reference",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )

        session.add_all([doc_match, doc_no_match])
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>Test</body></html>"
                    mock_extract.return_value = "Test"
                    mock_metadata.return_value = None

                    # Run fetch with pattern that matches only first doc
                    result = runner.invoke(
                        main,
                        [
                            "content",
                            "fetch",
                            "--include",
                            "*/docs/*",
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )

                    # Check command succeeded
                    assert result.exit_code == 0

        # Verify only matching document was fetched
        session.refresh(doc_match)
        session.refresh(doc_no_match)
        assert doc_match.ingestion_status == IngestionStatus.FETCHED
        assert doc_no_match.ingestion_status == IngestionStatus.NOT_FETCHED

    def test_fetch_handles_network_error(self, isolated_cli_runner):
        """Test that fetch handles network errors gracefully."""
        runner, project_dir = isolated_cli_runner

        # Create test document
        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()
        test_doc = Document(
            id=uuid4(),
            source_url="https://example.com/error",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(test_doc)
        session.commit()

        # Mock trafilatura to raise an exception
        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")

            # Run fetch
            result = runner.invoke(
                main,
                [
                    "content",
                    "fetch",
                    "--urls",
                    "https://example.com/error",
                    "--engine",
                    "trafilatura",
                    "--skip-index",
                ],
            )

            # Command should complete (not crash)
            # Note: exit_code might be 0 if errors are handled gracefully
            assert (
                "Network error" in result.output
                or "Error" in result.output
                or result.exit_code == 0
            )

        # Verify document status was updated to ERROR
        session.refresh(test_doc)
        assert test_doc.ingestion_status == IngestionStatus.ERROR

    def test_fetch_with_in_cluster_filter(self, isolated_cli_runner):
        """Test fetch with --in-cluster filter."""
        runner, project_dir = isolated_cli_runner

        # Create test documents and cluster
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import DocumentClusterEdge, TopicCluster

        session = get_session()

        # Create cluster
        cluster = TopicCluster(id=uuid4(), name="Tutorials", description="Tutorial content")
        session.add(cluster)

        # Create documents (one in cluster, one not)
        doc_in_cluster = Document(
            id=uuid4(),
            source_url="https://example.com/tutorial",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc_not_in_cluster = Document(
            id=uuid4(),
            source_url="https://example.com/other",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(doc_in_cluster)
        session.add(doc_not_in_cluster)
        session.commit()

        # Link doc to cluster
        edge = DocumentClusterEdge(id=uuid4(), document_id=doc_in_cluster.id, cluster_id=cluster.id)
        session.add(edge)
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>Test</body></html>"
                    mock_extract.return_value = "Test"
                    mock_metadata.return_value = None

                    # Run fetch with cluster filter
                    result = runner.invoke(
                        main,
                        [
                            "content",
                            "fetch",
                            "--in-cluster",
                            "Tutorials",
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )

                    # Check command succeeded
                    assert result.exit_code == 0

        # Verify only doc in cluster was fetched
        session.refresh(doc_in_cluster)
        session.refresh(doc_not_in_cluster)
        assert doc_in_cluster.ingestion_status == IngestionStatus.FETCHED
        assert doc_not_in_cluster.ingestion_status == IngestionStatus.NOT_FETCHED

    def test_fetch_with_ids_filter(self, isolated_cli_runner):
        """Test fetch with --ids option (comma-separated IDs)."""
        runner, project_dir = isolated_cli_runner

        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create test documents
        doc1 = Document(
            id=uuid4(),
            source_url="https://example.com/page1",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc2 = Document(
            id=uuid4(),
            source_url="https://example.com/page2",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc3 = Document(
            id=uuid4(),
            source_url="https://example.com/page3",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add_all([doc1, doc2, doc3])
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>Test</body></html>"
                    mock_extract.return_value = "Test content"
                    mock_metadata.return_value = None

                    # Run fetch with specific IDs (comma-separated)
                    ids_str = f"{doc1.id},{doc2.id}"
                    result = runner.invoke(
                        main,
                        [
                            "content",
                            "fetch",
                            "--ids",
                            ids_str,
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )

                    # Check command succeeded
                    assert result.exit_code == 0

        # Verify only specified documents were fetched
        session.refresh(doc1)
        session.refresh(doc2)
        session.refresh(doc3)
        assert doc1.ingestion_status == IngestionStatus.FETCHED
        assert doc2.ingestion_status == IngestionStatus.FETCHED
        assert doc3.ingestion_status == IngestionStatus.NOT_FETCHED

    def test_fetch_with_exclude_pattern(self, isolated_cli_runner):
        """Test fetch with --exclude refinement option."""
        runner, project_dir = isolated_cli_runner

        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create test documents - some matching include, some excluded
        doc_included = Document(
            id=uuid4(),
            source_url="https://example.com/docs/tutorial",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc_excluded = Document(
            id=uuid4(),
            source_url="https://example.com/docs/api/reference",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc_included2 = Document(
            id=uuid4(),
            source_url="https://example.com/docs/guide",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add_all([doc_included, doc_excluded, doc_included2])
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>Test</body></html>"
                    mock_extract.return_value = "Test content"
                    mock_metadata.return_value = None

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
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )

                    # Check command succeeded
                    assert result.exit_code == 0

        # Verify only non-excluded documents were fetched
        session.refresh(doc_included)
        session.refresh(doc_excluded)
        session.refresh(doc_included2)
        assert doc_included.ingestion_status == IngestionStatus.FETCHED
        assert doc_excluded.ingestion_status == IngestionStatus.NOT_FETCHED  # Excluded by pattern
        assert doc_included2.ingestion_status == IngestionStatus.FETCHED

    def test_fetch_with_limit(self, isolated_cli_runner):
        """Test fetch with --limit refinement option."""
        runner, project_dir = isolated_cli_runner

        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create multiple test documents
        docs = []
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/page{i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            docs.append(doc)
            session.add(doc)
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>Test</body></html>"
                    mock_extract.return_value = "Test content"
                    mock_metadata.return_value = None

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
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )

                    # Check command succeeded
                    assert result.exit_code == 0

        # Verify only 2 documents were fetched (first 2 based on query order)
        fetched_count = 0
        for doc in docs:
            session.refresh(doc)
            if doc.ingestion_status == IngestionStatus.FETCHED:
                fetched_count += 1

        assert fetched_count == 2

    def test_fetch_concurrency_warning_over_20(self, isolated_cli_runner):
        """Test warning when concurrency >20 without --force."""
        runner, project_dir = isolated_cli_runner

        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create test document
        doc = Document(
            id=uuid4(),
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(doc)
        session.commit()

        # Run fetch with high concurrency and decline confirmation
        result = runner.invoke(
            main,
            [
                "content",
                "fetch",
                "--urls",
                "https://example.com/test",
                "--concurrency",
                "25",
                "--engine",
                "trafilatura",
                "--skip-index",
            ],
            input="n\n",
        )  # User says "no" to confirmation

        # Check command showed warning and was aborted
        assert result.exit_code == 0  # Graceful abort
        assert "High concurrency" in result.output or "rate limit" in result.output
        assert "Aborted" in result.output

        # Verify document was NOT fetched
        session.refresh(doc)
        assert doc.ingestion_status == IngestionStatus.NOT_FETCHED

    def test_fetch_concurrency_warning_bypassed_with_force(self, isolated_cli_runner):
        """Test --force bypasses concurrency warning."""
        runner, project_dir = isolated_cli_runner

        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create test document
        doc = Document(
            id=uuid4(),
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add(doc)
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>Test</body></html>"
                    mock_extract.return_value = "Test content"
                    mock_metadata.return_value = None

                    # Run fetch with high concurrency and --force flag
                    result = runner.invoke(
                        main,
                        [
                            "content",
                            "fetch",
                            "--urls",
                            "https://example.com/test",
                            "--concurrency",
                            "25",
                            "--force",
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )

                    # Check command succeeded without asking for confirmation
                    assert result.exit_code == 0
                    assert "Continue anyway?" not in result.output

        # Verify document was fetched
        session.refresh(doc)
        assert doc.ingestion_status == IngestionStatus.FETCHED

    def test_fetch_with_refetch_flag(self, isolated_cli_runner):
        """Test --refetch includes already FETCHED documents."""
        runner, project_dir = isolated_cli_runner

        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create document that's already FETCHED
        doc_fetched = Document(
            id=uuid4(),
            source_url="https://example.com/fetched",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_path="example.com/fetched.md",
        )
        session.add(doc_fetched)
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>Refetched content</body></html>"
                    mock_extract.return_value = "Refetched content"
                    mock_metadata.return_value = None

                    # Run fetch with --refetch flag
                    result = runner.invoke(
                        main,
                        [
                            "content",
                            "fetch",
                            "--urls",
                            "https://example.com/fetched",
                            "--refetch",
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )

                    # Check command succeeded
                    assert result.exit_code == 0
                    assert mock_fetch.called  # Verify fetch was called

        # Verify document status is still FETCHED (refetched successfully)
        session.refresh(doc_fetched)
        assert doc_fetched.ingestion_status == IngestionStatus.FETCHED

    def test_fetch_json_output_format(self, isolated_cli_runner):
        """Validate JSON output structure."""
        runner, project_dir = isolated_cli_runner

        import json
        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create test documents
        doc1 = Document(
            id=uuid4(),
            source_url="https://example.com/page1",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        doc2 = Document(
            id=uuid4(),
            source_url="https://example.com/page2",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.NOT_FETCHED,
        )
        session.add_all([doc1, doc2])
        session.commit()

        # Run fetch with --format json and decline to proceed
        result = runner.invoke(
            main,
            ["content", "fetch", "--with-status", "NOT_FETCHED", "--format", "json"],
            input="n\n",
        )  # Decline to proceed

        # Check command executed
        assert result.exit_code == 0

        # Validate JSON output is present
        assert "total" in result.output
        assert "documents" in result.output

        # Extract and parse JSON from output
        # Find the JSON object by looking for opening and closing braces
        lines = result.output.split("\n")
        json_lines = []
        brace_count = 0
        in_json = False

        for line in lines:
            # Start capturing when we see the opening brace
            if "{" in line and not in_json:
                in_json = True

            if in_json:
                json_lines.append(line)
                # Count braces to know when JSON object is complete
                brace_count += line.count("{") - line.count("}")

                # Stop when braces are balanced
                if brace_count == 0:
                    break

        if json_lines:
            json_output = "\n".join(json_lines)
            parsed = json.loads(json_output)

            # Validate structure
            assert "total" in parsed
            assert "documents" in parsed
            assert parsed["total"] == 2
            assert len(parsed["documents"]) == 2
            assert all("id" in doc and "url" in doc for doc in parsed["documents"])
        else:
            # Fallback: just verify the basic structure is present
            assert '"total": 2' in result.output or '"total":2' in result.output
            assert '"documents"' in result.output

    def test_fetch_force_bypasses_batch_confirmation(self, isolated_cli_runner):
        """Test --force skips >100 docs confirmation."""
        runner, project_dir = isolated_cli_runner

        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create 101 test documents to trigger confirmation
        docs = []
        for i in range(101):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/page{i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            docs.append(doc)
            session.add(doc)
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>Test</body></html>"
                    mock_extract.return_value = "Test content"
                    mock_metadata.return_value = None

                    # Run fetch with --force flag (should skip confirmation)
                    result = runner.invoke(
                        main,
                        [
                            "content",
                            "fetch",
                            "--with-status",
                            "NOT_FETCHED",
                            "--force",
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )

                    # Check command succeeded without asking for confirmation
                    assert result.exit_code == 0
                    assert "Continue?" not in result.output  # No confirmation prompt
                    assert mock_fetch.called  # Verify fetch was executed

    def test_fetch_kurt_force_env_var(self, isolated_cli_runner):
        """Test KURT_FORCE=1 environment variable works."""
        runner, project_dir = isolated_cli_runner

        import os
        from uuid import uuid4

        from kurt.db.database import get_session

        session = get_session()

        # Create 101 test documents to trigger confirmation
        docs = []
        for i in range(101):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/page{i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            docs.append(doc)
            session.add(doc)
        session.commit()

        # Mock trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    with patch.dict(os.environ, {"KURT_FORCE": "1"}):
                        mock_fetch.return_value = "<html><body>Test</body></html>"
                        mock_extract.return_value = "Test content"
                        mock_metadata.return_value = None

                        # Run fetch WITHOUT --force flag but with KURT_FORCE env var
                        result = runner.invoke(
                            main,
                            [
                                "content",
                                "fetch",
                                "--with-status",
                                "NOT_FETCHED",
                                "--engine",
                                "trafilatura",
                                "--skip-index",
                            ],
                        )

                        # Check command succeeded without asking for confirmation
                        assert result.exit_code == 0
                        assert "Continue?" not in result.output  # No confirmation prompt
                        assert mock_fetch.called  # Verify fetch was executed

    def test_fetch_with_file_option(self, isolated_cli_runner):
        """Test fetch with --file option for local file ingestion."""
        runner, project_dir = isolated_cli_runner

        from kurt.config import load_config
        from kurt.db.database import get_session

        session = get_session()
        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create a test markdown file inside sources directory
        test_file = sources_dir / "test_article.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Test Article\n\nThis is test content.")

        # Run fetch with --file option
        # Note: Files are created with FETCHED status, so by default they're skipped
        # We need --refetch to actually process them, or we can verify the document was created
        result = runner.invoke(main, ["content", "fetch", "--file", str(test_file), "--skip-index"])

        # Check command succeeded (may show "already FETCHED" message)
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Should mention document creation
        assert "Created" in result.output or "document" in result.output

        # Verify document was created in database
        from sqlmodel import select

        from kurt.db.models import Document

        stmt = select(Document).where(Document.content_path == "test_article.md")
        doc = session.exec(stmt).first()

        assert doc is not None, "Document should be created"
        assert doc.title == "Test Article"  # Extracted from markdown heading
        assert doc.source_type == SourceType.FILE_UPLOAD
        assert doc.ingestion_status == IngestionStatus.FETCHED
        assert doc.content_path == "test_article.md"

    def test_fetch_with_files_option(self, isolated_cli_runner):
        """Test fetch with --files option for multiple local files."""
        runner, project_dir = isolated_cli_runner

        from kurt.config import load_config
        from kurt.db.database import get_session

        session = get_session()
        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create multiple test files inside sources directory
        test_file1 = sources_dir / "article1.md"
        test_file2 = sources_dir / "article2.md"

        test_file1.parent.mkdir(parents=True, exist_ok=True)
        test_file1.write_text("# First Article\n\nContent for first article.")
        test_file2.write_text("# Second Article\n\nContent for second article.")

        # Run fetch with --files option (comma-separated)
        files_str = f"{test_file1},{test_file2}"
        result = runner.invoke(main, ["content", "fetch", "--files", files_str, "--skip-index"])

        # Check command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Should mention document creation
        assert "Created 2 document" in result.output or "document" in result.output

        # Verify both documents were created
        from sqlmodel import select

        from kurt.db.models import Document

        stmt1 = select(Document).where(Document.content_path == "article1.md")
        doc1 = session.exec(stmt1).first()

        stmt2 = select(Document).where(Document.content_path == "article2.md")
        doc2 = session.exec(stmt2).first()

        assert doc1 is not None, "First document should be created"
        assert doc2 is not None, "Second document should be created"
        assert doc1.title == "First Article"
        assert doc2.title == "Second Article"
        assert doc1.source_type == SourceType.FILE_UPLOAD
        assert doc2.source_type == SourceType.FILE_UPLOAD
        assert doc1.ingestion_status == IngestionStatus.FETCHED
        assert doc2.ingestion_status == IngestionStatus.FETCHED

    def test_fetch_file_outside_sources_directory(self, isolated_cli_runner):
        """Test fetch copies files outside sources/ to sources/local/."""
        runner, project_dir = isolated_cli_runner

        import tempfile
        from pathlib import Path

        from kurt.config import load_config
        from kurt.db.database import get_session

        session = get_session()
        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create a temporary file OUTSIDE sources directory
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
            tmp.write("# External Article\n\nThis file is outside sources directory.")
            tmp_path = Path(tmp.name)

        try:
            # Run fetch with external file
            result = runner.invoke(
                main, ["content", "fetch", "--file", str(tmp_path), "--skip-index"]
            )

            # Check command succeeded
            assert result.exit_code == 0, f"Command failed: {result.output}"
            assert "Copied" in result.output  # Should mention copying to sources/local/
            assert "sources/local/" in result.output

            # Verify file was copied to sources/local/
            expected_copy = sources_dir / "local" / tmp_path.name
            assert expected_copy.exists(), "File should be copied to sources/local/"

            # Verify document was created with correct path
            from sqlmodel import select

            from kurt.db.models import Document

            expected_content_path = f"local/{tmp_path.name}"
            stmt = select(Document).where(Document.content_path == expected_content_path)
            doc = session.exec(stmt).first()

            assert doc is not None, "Document should be created"
            assert doc.title == "External Article"
            assert doc.source_type == SourceType.FILE_UPLOAD
            assert doc.ingestion_status == IngestionStatus.FETCHED

        finally:
            # Clean up temporary file
            if tmp_path.exists():
                tmp_path.unlink()

    def test_fetch_file_nonexistent(self, isolated_cli_runner):
        """Test fetch with non-existent file returns error."""
        runner, project_dir = isolated_cli_runner

        # Run fetch with non-existent file
        result = runner.invoke(
            main, ["content", "fetch", "--file", "/tmp/nonexistent_file.md", "--skip-index"]
        )

        # Check command shows error
        assert "File not found" in result.output or "Error" in result.output

    def test_fetch_file_title_from_filename(self, isolated_cli_runner):
        """Test fetch extracts title from filename when no markdown heading."""
        runner, project_dir = isolated_cli_runner

        from kurt.config import load_config
        from kurt.db.database import get_session

        session = get_session()
        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create a test file WITHOUT markdown heading
        test_file = sources_dir / "my-article-title.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Just plain text without a heading.")

        # Run fetch
        result = runner.invoke(main, ["content", "fetch", "--file", str(test_file), "--skip-index"])

        # Check command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify title was extracted from filename
        from sqlmodel import select

        from kurt.db.models import Document

        stmt = select(Document).where(Document.content_path == "my-article-title.md")
        doc = session.exec(stmt).first()

        assert doc is not None
        assert doc.title == "my-article-title"  # Filename without extension

    def test_fetch_file_and_url_separate_calls(self, isolated_cli_runner):
        """Test fetch with --file and --url in separate calls."""
        runner, project_dir = isolated_cli_runner

        from kurt.config import load_config
        from kurt.db.database import get_session

        session = get_session()
        config = load_config()
        sources_dir = config.get_absolute_sources_path()

        # Create a test file
        test_file = sources_dir / "local_article.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Local Article\n\nLocal content.")

        # First, fetch the file
        result1 = runner.invoke(
            main, ["content", "fetch", "--file", str(test_file), "--skip-index"]
        )
        assert result1.exit_code == 0, f"File fetch failed: {result1.output}"

        # Then, fetch the URL with mocked trafilatura
        with patch("trafilatura.fetch_url") as mock_fetch:
            with patch("trafilatura.extract") as mock_extract:
                with patch("trafilatura.extract_metadata") as mock_metadata:
                    mock_fetch.return_value = "<html><body>URL content</body></html>"
                    mock_extract.return_value = "URL content"
                    mock_metadata.return_value = None

                    result2 = runner.invoke(
                        main,
                        [
                            "content",
                            "fetch",
                            "--url",
                            "https://example.com/article",
                            "--engine",
                            "trafilatura",
                            "--skip-index",
                        ],
                    )
                    assert result2.exit_code == 0, f"URL fetch failed: {result2.output}"

        # Verify both documents were created
        from sqlmodel import select

        from kurt.db.models import Document

        # Check file document
        stmt_file = select(Document).where(Document.content_path == "local_article.md")
        doc_file = session.exec(stmt_file).first()
        assert doc_file is not None
        assert doc_file.source_type == SourceType.FILE_UPLOAD
        assert doc_file.title == "Local Article"
        assert doc_file.ingestion_status == IngestionStatus.FETCHED

        # Check URL document
        stmt_url = select(Document).where(Document.source_url == "https://example.com/article")
        doc_url = session.exec(stmt_url).first()
        assert doc_url is not None
        assert doc_url.source_type == SourceType.URL
        assert doc_url.ingestion_status == IngestionStatus.FETCHED
