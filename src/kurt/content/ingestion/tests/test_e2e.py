"""
End-to-end tests for fetch pipeline.

Tests the complete fetch workflow with mocked external calls.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.ingestion.step_fetch import (
    FetchConfig,
    fetch,
)
from kurt.core import PipelineContext


class TestFetchPipelineE2E:
    """End-to-end tests for fetch pipeline."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock()
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
    def mock_config(self):
        """Create mock config."""
        config = MagicMock(spec=FetchConfig)
        config.fetch_engine = "trafilatura"
        config.embedding_max_chars = 1000
        return config

    def _create_mock_reference(self, documents: list[dict]):
        """Create a mock Reference that returns the documents DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(documents)
        return mock_ref

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    def test_e2e_web_document_success(
        self,
        mock_save_links,
        mock_save_content,
        mock_generate_embedding,
        mock_extract,
        mock_metadata,
        mock_fetch_url,
        mock_writer,
        mock_ctx,
        mock_config,
    ):
        """Test complete flow: fetch web page -> extract -> embed -> save -> links."""
        doc_id = str(uuid4())
        source_url = "https://docs.example.com/getting-started"

        # Mock trafilatura fetch
        mock_fetch_url.return_value = """
        <html>
            <head><title>Getting Started Guide</title></head>
            <body>
                <h1>Getting Started</h1>
                <p>Welcome to our documentation.</p>
                <p>See <a href="/api">API Reference</a> for details.</p>
            </body>
        </html>
        """

        # Mock trafilatura metadata extraction
        mock_metadata_obj = MagicMock()
        mock_metadata_obj.title = "Getting Started Guide"
        mock_metadata_obj.author = "Docs Team"
        mock_metadata_obj.date = "2024-01-15"
        mock_metadata_obj.description = "Learn how to get started"
        mock_metadata_obj.fingerprint = "abc123def"
        mock_metadata.return_value = mock_metadata_obj

        # Mock trafilatura content extraction
        mock_extract.return_value = """# Getting Started

Welcome to our documentation.

See [API Reference](/api) for details."""

        # Mock embedding generation (1536 dims = 6144 bytes)
        mock_generate_embedding.return_value = b"\x00" * 6144

        # Mock save content
        mock_save_content.return_value = {
            "content_path": "sources/docs.example.com/getting-started.md"
        }

        # Mock link extraction returns internal links
        mock_save_links.return_value = 1

        # Create input documents
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

        # Execute pipeline
        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=mock_config,
        )

        # Verify result
        assert result["documents_fetched"] == 1
        assert result["documents_failed"] == 0

        # Verify fetch was called correctly
        mock_fetch_url.assert_called_once_with(source_url)

        # Verify embedding was generated
        mock_generate_embedding.assert_called_once()

        # Verify content was saved
        mock_save_content.assert_called_once()

        # Verify links were extracted and saved
        mock_save_links.assert_called_once()

        # Verify output row
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        row = rows[0]
        assert row.document_id == doc_id
        assert row.status == "FETCHED"
        assert row.embedding_dims == 1536  # 6144 bytes / 4
        assert row.fetch_engine == "trafilatura"
        assert row.metadata_json["title"] == "Getting Started Guide"

    @patch("kurt.content.ingestion.step_fetch.fetch_from_cms")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    def test_e2e_cms_document_success(
        self,
        mock_save_links,
        mock_save_content,
        mock_generate_embedding,
        mock_fetch_cms,
        mock_writer,
        mock_ctx,
        mock_config,
    ):
        """Test complete flow: fetch CMS doc -> embed -> save -> links."""
        doc_id = str(uuid4())

        # Mock CMS fetch
        mock_fetch_cms.return_value = (
            "# Blog Post\n\nThis is a blog post from our CMS.",
            {"title": "Blog Post", "author": "Jane Doe"},
            "https://blog.example.com/posts/my-post",
        )

        mock_generate_embedding.return_value = b"\x00" * 6144
        mock_save_content.return_value = {"content_path": "sources/sanity/prod/my-post.md"}
        mock_save_links.return_value = 0

        mock_documents = self._create_mock_reference(
            [
                {
                    "id": doc_id,
                    "source_url": "sanity/prod/article/post-123",
                    "cms_platform": "sanity",
                    "cms_instance": "prod",
                    "cms_document_id": "post-123",
                    "discovery_url": "https://blog.example.com",
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "ingestion_fetch"}

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=mock_config,
        )

        assert result["documents_fetched"] == 1

        # Verify CMS fetch was called
        mock_fetch_cms.assert_called_once_with(
            platform="sanity",
            instance="prod",
            cms_document_id="post-123",
            discovery_url="https://blog.example.com",
        )

        # Verify public URL was set
        rows = mock_writer.write.call_args[0][0]
        assert rows[0].public_url == "https://blog.example.com/posts/my-post"

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    @patch("kurt.db.database.get_session")
    def test_e2e_batch_with_failures(
        self,
        mock_get_session,
        mock_save_links,
        mock_save_content,
        mock_generate_embedding,
        mock_extract,
        mock_metadata,
        mock_fetch_url,
        mock_writer,
        mock_ctx,
        mock_config,
    ):
        """Test batch processing with mixed success/failure."""
        doc_ids = [str(uuid4()) for _ in range(3)]

        # First doc succeeds, second fails, third succeeds
        mock_fetch_url.side_effect = [
            "<html><body>Doc 1</body></html>",
            None,  # Download fails
            "<html><body>Doc 3</body></html>",
        ]

        mock_metadata_obj = MagicMock()
        mock_metadata_obj.title = "Test"
        mock_metadata_obj.author = None
        mock_metadata_obj.date = None
        mock_metadata_obj.description = None
        mock_metadata_obj.fingerprint = "fp123"
        mock_metadata.return_value = mock_metadata_obj
        mock_extract.return_value = "# Content"

        mock_generate_embedding.return_value = b"\x00" * 6144
        mock_save_content.return_value = {"content_path": "test.md"}
        mock_save_links.return_value = 0
        mock_get_session.return_value = MagicMock()

        documents = [
            {
                "id": doc_id,
                "source_url": f"https://example.com/doc{i}",
                "cms_platform": None,
                "cms_instance": None,
                "cms_document_id": None,
                "discovery_url": None,
            }
            for i, doc_id in enumerate(doc_ids)
        ]

        mock_documents = self._create_mock_reference(documents)
        mock_writer.write.return_value = {"rows_written": 3, "table_name": "ingestion_fetch"}

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=mock_config,
        )

        # Verify counts
        assert result["documents_fetched"] == 2
        assert result["documents_failed"] == 1

        # Verify statuses
        rows = mock_writer.write.call_args[0][0]
        statuses = [r.status for r in rows]
        assert statuses.count("FETCHED") == 2
        assert statuses.count("ERROR") == 1

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    @patch("kurt.content.ingestion.step_fetch.generate_document_embedding")
    @patch("kurt.content.ingestion.step_fetch.save_document_content_and_metadata")
    @patch("kurt.content.ingestion.step_fetch.save_document_links")
    def test_e2e_embedding_failure_continues(
        self,
        mock_save_links,
        mock_save_content,
        mock_generate_embedding,
        mock_extract,
        mock_metadata,
        mock_fetch_url,
        mock_writer,
        mock_ctx,
        mock_config,
    ):
        """Test that embedding failure doesn't stop document processing."""
        doc_id = str(uuid4())

        mock_fetch_url.return_value = "<html><body>Content</body></html>"
        mock_metadata.return_value = MagicMock(
            title="Test", author=None, date=None, description=None, fingerprint="fp"
        )
        mock_extract.return_value = "# Content"

        # Embedding fails
        mock_generate_embedding.side_effect = Exception("OpenAI API error")

        mock_save_content.return_value = {"content_path": "test.md"}
        mock_save_links.return_value = 0

        mock_documents = self._create_mock_reference(
            [
                {
                    "id": doc_id,
                    "source_url": "https://example.com/doc",
                    "cms_platform": None,
                    "cms_instance": None,
                    "cms_document_id": None,
                    "discovery_url": None,
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "ingestion_fetch"}

        result = fetch(
            ctx=mock_ctx,
            documents=mock_documents,
            writer=mock_writer,
            config=mock_config,
        )

        # Document should still succeed
        assert result["documents_fetched"] == 1
        assert result["documents_failed"] == 0

        # But embedding_dims should be 0
        rows = mock_writer.write.call_args[0][0]
        assert rows[0].embedding_dims == 0
        assert rows[0].status == "FETCHED"
