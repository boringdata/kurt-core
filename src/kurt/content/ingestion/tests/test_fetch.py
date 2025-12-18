"""
Unit tests for the fetch model.

Tests content fetching, embedding generation, link extraction, and error handling.
Uses mocks at the library level (trafilatura, etc.) to avoid network calls.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.ingestion.step_fetch import (
    FetchRow,
    fetch,
)
from kurt.core import PipelineContext, TableWriter


class TestFetchModel:
    """Test suite for the fetch model."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "ingestion_fetch"}
        return writer

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @pytest.fixture
    def default_config(self):
        """Create default FetchConfig with resolved values."""
        # Create config and manually set values (bypassing ConfigParam)
        config = MagicMock()
        config.fetch_engine = "trafilatura"
        config.embedding_max_chars = 1000
        return config

    def _create_mock_reference(self, documents: list[dict]):
        """Create a mock Reference that returns the documents DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(documents)
        return mock_ref

    # =========================================================================
    # Basic Fetch Tests
    # =========================================================================

    @patch("kurt.content.ingestion.step_fetch.fetch_from_web")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.extract_document_links")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    def test_single_web_document_fetch(
        self,
        mock_save_links,
        mock_extract_links,
        mock_save_content,
        mock_generate_embedding,
        mock_fetch_web,
        mock_writer,
        mock_ctx,
        default_config,
    ):
        """Test fetching a single web document."""
        doc_id = str(uuid4())
        source_url = "https://example.com/article"

        # Setup mocks
        mock_fetch_web.return_value = (
            "# Title\n\nTest content",
            {"title": "Test", "fingerprint": "abc123"},
        )
        mock_generate_embedding.return_value = b"\x00" * 1536 * 4  # 1536 floats
        mock_save_content.return_value = {"content_path": "sources/example.com/article.md"}
        mock_extract_links.return_value = [
            {"url": "https://example.com/other", "anchor_text": "other"}
        ]
        mock_save_links.return_value = 1

        mock_documents = self._create_mock_reference(
            [
                {
                    "id": doc_id,
                    "source_url": source_url,
                    "cms_platform": None,
                    "cms_instance": None,
                    "cms_document_id": None,
                    "discovery_url": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "ingestion_fetch",
        }

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=default_config,
        )

        # Verify result
        assert result["rows_written"] == 1
        assert result["documents_fetched"] == 1
        assert result["documents_failed"] == 0

        # Verify fetch was called
        mock_fetch_web.assert_called_once_with(
            source_url=source_url,
            fetch_engine="trafilatura",
        )

        # Verify written row
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].document_id == doc_id
        assert rows[0].status == "FETCHED"
        assert rows[0].content_length == len("# Title\n\nTest content")
        assert rows[0].links_extracted == 1

    @patch("kurt.content.ingestion.step_fetch.fetch_from_cms")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.extract_document_links")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    def test_cms_document_fetch(
        self,
        mock_save_links,
        mock_extract_links,
        mock_save_content,
        mock_generate_embedding,
        mock_fetch_cms,
        mock_writer,
        mock_ctx,
        default_config,
    ):
        """Test fetching a CMS document."""
        doc_id = str(uuid4())

        # Setup mocks
        mock_fetch_cms.return_value = (
            "# CMS Article\n\nCMS content here",
            {"title": "CMS Article", "fingerprint": "cms123"},
            "https://technically.dev/posts/article",
        )
        mock_generate_embedding.return_value = b"\x00" * 1536 * 4
        mock_save_content.return_value = {"content_path": "sources/sanity/prod/article.md"}
        mock_extract_links.return_value = []
        mock_save_links.return_value = 0

        mock_documents = self._create_mock_reference(
            [
                {
                    "id": doc_id,
                    "source_url": "sanity/prod/article/abc123",
                    "cms_platform": "sanity",
                    "cms_instance": "prod",
                    "cms_document_id": "abc123",
                    "discovery_url": "https://technically.dev",
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "ingestion_fetch",
        }

        fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=default_config,
        )

        # Verify CMS fetch was called
        mock_fetch_cms.assert_called_once_with(
            platform="sanity",
            instance="prod",
            cms_document_id="abc123",
            discovery_url="https://technically.dev",
        )

        # Verify written row has public_url
        rows = mock_writer.write.call_args[0][0]
        assert rows[0].public_url == "https://technically.dev/posts/article"

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    @patch("kurt.content.ingestion.step_fetch.fetch_from_web")
    @patch("kurt.db.database.get_session")
    def test_fetch_error_handling(
        self,
        mock_get_session,
        mock_fetch_web,
        mock_writer,
        mock_ctx,
        default_config,
    ):
        """Test error handling when fetch fails."""
        doc_id = str(uuid4())

        # Simulate fetch failure
        mock_fetch_web.side_effect = Exception("Network timeout")
        mock_get_session.return_value = MagicMock()  # Mock session for error marking

        mock_documents = self._create_mock_reference(
            [
                {
                    "id": doc_id,
                    "source_url": "https://example.com/broken",
                    "cms_platform": None,
                    "cms_instance": None,
                    "cms_document_id": None,
                    "discovery_url": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "ingestion_fetch",
        }

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=default_config,
        )

        # Verify error was recorded
        assert result["documents_fetched"] == 0
        assert result["documents_failed"] == 1

        # Verify error row was written
        rows = mock_writer.write.call_args[0][0]
        assert rows[0].status == "ERROR"
        assert "Network timeout" in rows[0].error

    @patch("kurt.content.ingestion.step_fetch.fetch_from_web")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.extract_document_links")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    def test_embedding_failure_continues(
        self,
        mock_save_links,
        mock_extract_links,
        mock_save_content,
        mock_generate_embedding,
        mock_fetch_web,
        mock_writer,
        mock_ctx,
        default_config,
    ):
        """Test that embedding failure doesn't stop document processing."""
        doc_id = str(uuid4())

        mock_fetch_web.return_value = ("Content", {"title": "Test"})
        mock_generate_embedding.side_effect = Exception("Embedding API error")
        mock_save_content.return_value = {"content_path": "sources/test.md"}
        mock_extract_links.return_value = []
        mock_save_links.return_value = 0

        mock_documents = self._create_mock_reference(
            [
                {
                    "id": doc_id,
                    "source_url": "https://example.com/article",
                    "cms_platform": None,
                    "cms_instance": None,
                    "cms_document_id": None,
                    "discovery_url": None,
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "ingestion_fetch",
        }

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=default_config,
        )

        # Document should still be saved successfully
        assert result["documents_fetched"] == 1
        rows = mock_writer.write.call_args[0][0]
        assert rows[0].status == "FETCHED"
        assert rows[0].embedding_dims == 0  # No embedding

    # =========================================================================
    # Batch Processing Tests
    # =========================================================================

    @patch("kurt.content.ingestion.step_fetch.fetch_from_web")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.extract_document_links")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    def test_batch_processing(
        self,
        mock_save_links,
        mock_extract_links,
        mock_save_content,
        mock_generate_embedding,
        mock_fetch_web,
        mock_writer,
        mock_ctx,
        default_config,
    ):
        """Test processing multiple documents."""
        doc_ids = [str(uuid4()) for _ in range(3)]

        mock_fetch_web.return_value = ("Content", {"title": "Test"})
        mock_generate_embedding.return_value = b"\x00" * 1536 * 4
        mock_save_content.return_value = {"content_path": "sources/test.md"}
        mock_extract_links.return_value = []
        mock_save_links.return_value = 0

        documents = [
            {
                "id": doc_id,
                "source_url": f"https://example.com/article{i}",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
                "discovery_url": None,
            }
            for i, doc_id in enumerate(doc_ids)
        ]

        mock_documents = self._create_mock_reference(documents)

        mock_writer.write.return_value = {
            "rows_written": 3,
            "table_name": "ingestion_fetch",
        }

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=default_config,
        )

        assert result["documents_fetched"] == 3
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3
        assert all(r.status == "FETCHED" for r in rows)

    @patch("kurt.content.ingestion.step_fetch.fetch_from_web")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.extract_document_links")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    @patch("kurt.db.database.get_session")
    def test_batch_mixed_success_failure(
        self,
        mock_get_session,
        mock_save_links,
        mock_extract_links,
        mock_save_content,
        mock_generate_embedding,
        mock_fetch_web,
        mock_writer,
        mock_ctx,
        default_config,
    ):
        """Test batch with some successes and some failures."""
        doc_ids = [str(uuid4()) for _ in range(3)]

        # First succeeds, second fails, third succeeds
        mock_fetch_web.side_effect = [
            ("Content 1", {"title": "Test 1"}),
            Exception("Fetch failed"),
            ("Content 3", {"title": "Test 3"}),
        ]
        mock_generate_embedding.return_value = b"\x00" * 1536 * 4
        mock_save_content.return_value = {"content_path": "sources/test.md"}
        mock_extract_links.return_value = []
        mock_save_links.return_value = 0
        mock_get_session.return_value = MagicMock()

        documents = [
            {
                "id": doc_id,
                "source_url": f"https://example.com/article{i}",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
                "discovery_url": None,
            }
            for i, doc_id in enumerate(doc_ids)
        ]

        mock_documents = self._create_mock_reference(documents)

        mock_writer.write.return_value = {
            "rows_written": 3,
            "table_name": "ingestion_fetch",
        }

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=default_config,
        )

        assert result["documents_fetched"] == 2
        assert result["documents_failed"] == 1

        rows = mock_writer.write.call_args[0][0]
        statuses = [r.status for r in rows]
        assert statuses.count("FETCHED") == 2
        assert statuses.count("ERROR") == 1

    # =========================================================================
    # Empty/Edge Case Tests
    # =========================================================================

    def test_empty_documents(self, mock_writer, mock_ctx, default_config):
        """Test handling of empty documents DataFrame."""
        mock_documents = self._create_mock_reference([])

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=default_config,
        )

        assert result["rows_written"] == 0
        assert result["documents_processed"] == 0
        mock_writer.write.assert_not_called()

    # =========================================================================
    # Schema Tests
    # =========================================================================

    def test_output_schema_fields(self):
        """Test FetchRow schema has all required fields."""
        row = FetchRow(
            document_id="test-id",
            status="FETCHED",
            content_length=100,
            content_hash="abc123",
            content_path="sources/test.md",
            embedding_dims=1536,
            links_extracted=5,
            fetch_engine="trafilatura",
            public_url="https://example.com",
            metadata_json={"title": "Test"},
        )

        assert row.document_id == "test-id"
        assert row.status == "FETCHED"
        assert row.content_length == 100
        assert row.links_extracted == 5
        assert row.metadata_json == {"title": "Test"}

    def test_output_schema_defaults(self):
        """Test FetchRow schema defaults."""
        row = FetchRow(document_id="test-id")

        assert row.status == "pending"
        assert row.content_length == 0
        assert row.embedding_dims == 0
        assert row.links_extracted == 0
        assert row.content_hash is None
        assert row.content_path is None
