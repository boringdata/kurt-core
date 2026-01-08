"""Tests for fetch models."""

from kurt_new.workflows.fetch import FetchDocument, FetchStatus


class TestFetchStatus:
    """Test suite for FetchStatus enum."""

    def test_status_values(self):
        """Test FetchStatus enum values."""
        assert FetchStatus.PENDING.value == "PENDING"
        assert FetchStatus.FETCHED.value == "FETCHED"
        assert FetchStatus.ERROR.value == "ERROR"

    def test_status_from_string(self):
        """Test creating FetchStatus from string."""
        assert FetchStatus("PENDING") == FetchStatus.PENDING
        assert FetchStatus("FETCHED") == FetchStatus.FETCHED
        assert FetchStatus("ERROR") == FetchStatus.ERROR


class TestFetchDocument:
    """Test suite for FetchDocument model."""

    def test_document_creation(self):
        """Test creating a FetchDocument."""
        doc = FetchDocument(document_id="test-doc-1")

        assert doc.document_id == "test-doc-1"
        assert doc.status == FetchStatus.PENDING
        assert doc.content_length == 0
        assert doc.content_hash is None
        assert doc.fetch_engine is None
        assert doc.public_url is None
        assert doc.embedding is None
        assert doc.error is None
        assert doc.metadata_json is None

    def test_document_with_fetched_status(self):
        """Test FetchDocument with FETCHED status and content."""
        doc = FetchDocument(
            document_id="test-doc-2",
            status=FetchStatus.FETCHED,
            content_length=1500,
            content_hash="abc123",
            fetch_engine="trafilatura",
            public_url="https://example.com/doc",
        )

        assert doc.status == FetchStatus.FETCHED
        assert doc.content_length == 1500
        assert doc.content_hash == "abc123"
        assert doc.fetch_engine == "trafilatura"
        assert doc.public_url == "https://example.com/doc"

    def test_document_with_error(self):
        """Test FetchDocument with error status."""
        doc = FetchDocument(
            document_id="test-doc-3",
            status=FetchStatus.ERROR,
            error="Connection timeout",
            fetch_engine="httpx",
        )

        assert doc.status == FetchStatus.ERROR
        assert doc.error == "Connection timeout"
        assert doc.content_length == 0

    def test_document_with_embedding(self):
        """Test FetchDocument with embedding bytes."""
        embedding_bytes = b"\x00\x00\x80?\x00\x00\x00@"  # [1.0, 2.0] as float32
        doc = FetchDocument(
            document_id="test-doc-4",
            status=FetchStatus.FETCHED,
            embedding=embedding_bytes,
        )

        assert doc.embedding == embedding_bytes

    def test_document_with_metadata(self):
        """Test FetchDocument with metadata_json."""
        metadata = {
            "title": "Test Document",
            "author": "John Doe",
            "fingerprint": "xyz789",
        }
        doc = FetchDocument(
            document_id="test-doc-5",
            status=FetchStatus.FETCHED,
            metadata_json=metadata,
        )

        assert doc.metadata_json == metadata
        assert doc.metadata_json["title"] == "Test Document"

    def test_document_tablename(self):
        """Test FetchDocument table name."""
        assert FetchDocument.__tablename__ == "fetch_documents"

    def test_document_with_content_path(self):
        """Test FetchDocument with content_path field."""
        doc = FetchDocument(
            document_id="test-doc-6",
            status=FetchStatus.FETCHED,
            content_length=2000,
            content_path="ab/cd/test-doc-6.md",
        )

        assert doc.content_path == "ab/cd/test-doc-6.md"

    def test_document_content_path_default_none(self):
        """Test FetchDocument content_path defaults to None."""
        doc = FetchDocument(document_id="test-doc-7")

        assert doc.content_path is None
