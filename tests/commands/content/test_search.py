"""
Unit tests for 'content search' command.

═══════════════════════════════════════════════════════════════════════════════
TEST COVERAGE
═══════════════════════════════════════════════════════════════════════════════

TestContentSearchCommand
────────────────────────────────────────────────────────────────────────────────
  ✓ test_search_basic
      → Tests basic vector search with a simple query

  ✓ test_search_with_include_pattern
      → Tests --include pattern filtering

  ✓ test_search_max_results
      → Tests --max-results limiting

  ✓ test_search_min_similarity
      → Tests --min-similarity threshold

  ✓ test_search_json_output
      → Tests --format json output

  ✓ test_search_no_matches
      → Tests behavior when no similar documents found

  ✓ test_search_help
      → Tests help text display
"""

import json
from unittest.mock import patch
from uuid import uuid4

from kurt.cli import main


class TestContentSearchCommand:
    """Tests for 'content search' command."""

    def test_search_basic(self, isolated_cli_runner):
        """Test basic vector search with a simple query."""
        runner, project_dir = isolated_cli_runner

        # Create a mock document with embedding
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            title="Test Document",
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(doc)
        session.commit()

        # Mock the embedding generation and search
        with patch("kurt.content.embeddings.generate_embeddings") as mock_gen:
            with patch("kurt.db.sqlite.SQLiteClient.search_similar_documents") as mock_search:
                # Mock embedding generation
                mock_gen.return_value = [[0.1] * 512]  # Mock 512-dim embedding

                # Mock search results - return the document we created
                mock_search.return_value = [(str(doc_id), 0.85)]

                result = runner.invoke(main, ["content", "search", "test query"])

                if result.exit_code != 0:
                    print(f"Exit code: {result.exit_code}")
                    print(f"Output: {result.output}")

                assert result.exit_code == 0
                assert "Test Document" in result.output
                assert "85" in result.output  # Similarity percentage

    def test_search_with_include_pattern(self, isolated_cli_runner):
        """Test --include pattern filtering."""
        runner, project_dir = isolated_cli_runner

        # Create documents with different URLs
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()

        doc1_id = uuid4()
        doc1 = Document(
            id=doc1_id,
            title="Docs Page",
            source_url="https://example.com/docs/auth",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )

        doc2_id = uuid4()
        doc2 = Document(
            id=doc2_id,
            title="Blog Post",
            source_url="https://example.com/blog/auth",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )

        session.add(doc1)
        session.add(doc2)
        session.commit()

        # Mock embeddings and search
        with patch("kurt.content.embeddings.generate_embeddings") as mock_gen:
            with patch("kurt.db.sqlite.SQLiteClient.search_similar_documents") as mock_search:
                mock_gen.return_value = [[0.1] * 512]
                # Return both documents
                mock_search.return_value = [
                    (str(doc1_id), 0.85),
                    (str(doc2_id), 0.80),
                ]

                # Search with include pattern for docs only
                result = runner.invoke(
                    main, ["content", "search", "authentication", "--include", "*/docs/*"]
                )

                assert result.exit_code == 0
                assert "Docs Page" in result.output
                assert "Blog Post" not in result.output  # Should be filtered out

    def test_search_max_results(self, isolated_cli_runner):
        """Test --max-results limiting."""
        runner, project_dir = isolated_cli_runner

        # Create multiple documents
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()
        doc_ids = []

        for i in range(5):
            doc_id = uuid4()
            doc_ids.append(doc_id)
            doc = Document(
                id=doc_id,
                title=f"Doc {i}",
                source_url=f"https://example.com/doc{i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.FETCHED,
            )
            session.add(doc)

        session.commit()

        # Mock embeddings and search
        with patch("kurt.content.embeddings.generate_embeddings") as mock_gen:
            with patch("kurt.db.sqlite.SQLiteClient.search_similar_documents") as mock_search:
                mock_gen.return_value = [[0.1] * 512]

                # Return results but only 2 based on max_results
                mock_search.return_value = [
                    (str(doc_ids[0]), 0.90),
                    (str(doc_ids[1]), 0.85),
                ]

                result = runner.invoke(main, ["content", "search", "test", "--max-results", "2"])

                assert result.exit_code == 0
                # Should call search with limit=2
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["limit"] == 2

    def test_search_min_similarity(self, isolated_cli_runner):
        """Test --min-similarity threshold."""
        runner, project_dir = isolated_cli_runner

        # Create a document
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            title="Test Doc",
            source_url="https://example.com/test",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(doc)
        session.commit()

        # Mock embeddings and search
        with patch("kurt.content.embeddings.generate_embeddings") as mock_gen:
            with patch("kurt.db.sqlite.SQLiteClient.search_similar_documents") as mock_search:
                mock_gen.return_value = [[0.1] * 512]
                mock_search.return_value = [(str(doc_id), 0.95)]

                result = runner.invoke(
                    main, ["content", "search", "test", "--min-similarity", "0.85"]
                )

                assert result.exit_code == 0
                # Should call search with min_similarity=0.85
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["min_similarity"] == 0.85

    def test_search_json_output(self, isolated_cli_runner):
        """Test --format json output."""
        runner, project_dir = isolated_cli_runner

        # Create a document
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            title="JSON Test",
            source_url="https://example.com/json",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(doc)
        session.commit()

        # Mock embeddings and search
        with patch("kurt.content.embeddings.generate_embeddings") as mock_gen:
            with patch("kurt.db.sqlite.SQLiteClient.search_similar_documents") as mock_search:
                mock_gen.return_value = [[0.1] * 512]
                mock_search.return_value = [(str(doc_id), 0.82)]

                result = runner.invoke(main, ["content", "search", "test", "--format", "json"])

                assert result.exit_code == 0

                # Verify JSON structure
                output = json.loads(result.output)
                assert "query" in output
                assert output["query"] == "test"
                assert "total_matches" in output
                assert output["total_matches"] == 1
                assert "results" in output
                assert isinstance(output["results"], list)
                assert len(output["results"]) == 1
                assert output["results"][0]["title"] == "JSON Test"
                assert output["results"][0]["similarity"] == 0.82

    def test_search_no_matches(self, isolated_cli_runner):
        """Test behavior when no similar documents found."""
        runner, project_dir = isolated_cli_runner

        # Mock embeddings and search with no results
        with patch("kurt.content.embeddings.generate_embeddings") as mock_gen:
            with patch("kurt.db.sqlite.SQLiteClient.search_similar_documents") as mock_search:
                mock_gen.return_value = [[0.1] * 512]
                mock_search.return_value = []  # No results

                result = runner.invoke(main, ["content", "search", "nonexistent"])

                # Should succeed but show no matches
                assert result.exit_code == 0
                assert "No similar documents found" in result.output
                assert "Try lowering --min-similarity" in result.output

    def test_search_help(self, isolated_cli_runner):
        """Test help text display."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(main, ["content", "search", "--help"])

        assert result.exit_code == 0
        assert "semantic" in result.output.lower() or "vector" in result.output.lower()
        assert "--include" in result.output
        assert "--max-results" in result.output
        assert "--min-similarity" in result.output
        assert "--format" in result.output
