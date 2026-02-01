"""Tests for MapDocument and MapStatus models."""

from kurt.tools.map.models import MapDocument, MapStatus


class TestMapStatus:
    """Test suite for MapStatus enum."""

    def test_status_values(self):
        """Test MapStatus enum values."""
        assert MapStatus.PENDING.value == "PENDING"
        assert MapStatus.SUCCESS.value == "SUCCESS"
        assert MapStatus.ERROR.value == "ERROR"

    def test_status_is_string_enum(self):
        """Test that MapStatus inherits from str."""
        assert isinstance(MapStatus.SUCCESS, str)
        assert MapStatus.SUCCESS == "SUCCESS"

    def test_status_members(self):
        """Test all status members exist."""
        members = list(MapStatus)
        assert len(members) == 3
        assert MapStatus.PENDING in members
        assert MapStatus.SUCCESS in members
        assert MapStatus.ERROR in members


class TestMapDocument:
    """Test suite for MapDocument model."""

    def test_document_import(self):
        """Test that MapDocument can be imported."""
        assert MapDocument is not None

    def test_document_table_name(self):
        """Test MapDocument table name."""
        assert MapDocument.__tablename__ == "map_documents"

    def test_document_schema_fields(self):
        """Test MapDocument has expected fields."""
        doc = MapDocument(
            document_id="test-doc-123",
            source_url="https://example.com/page",
            source_type="url",
            discovery_method="sitemap",
            status=MapStatus.SUCCESS,
            is_new=True,
        )

        assert doc.document_id == "test-doc-123"
        assert doc.source_url == "https://example.com/page"
        assert doc.source_type == "url"
        assert doc.discovery_method == "sitemap"
        assert doc.status == MapStatus.SUCCESS
        assert doc.is_new is True

    def test_document_defaults(self):
        """Test MapDocument default values."""
        doc = MapDocument(document_id="test-123")

        assert doc.source_url == ""
        assert doc.source_type == "url"
        assert doc.discovery_method == ""
        assert doc.discovery_url is None
        assert doc.status == MapStatus.SUCCESS
        assert doc.is_new is True
        assert doc.title is None
        assert doc.content_hash is None
        assert doc.error is None
        assert doc.metadata_json is None

    def test_document_with_error(self):
        """Test MapDocument with error state."""
        doc = MapDocument(
            document_id="error-doc-456",
            status=MapStatus.ERROR,
            error="Connection timeout",
        )

        assert doc.status == MapStatus.ERROR
        assert doc.error == "Connection timeout"

    def test_document_with_metadata(self):
        """Test MapDocument with metadata_json."""
        metadata = {"author": "John", "tags": ["guide", "tutorial"]}
        doc = MapDocument(
            document_id="meta-doc-789",
            metadata_json=metadata,
        )

        assert doc.metadata_json == metadata
        assert doc.metadata_json["author"] == "John"
        assert "guide" in doc.metadata_json["tags"]

    def test_document_existing_status(self):
        """Test MapDocument with EXISTING status."""
        doc = MapDocument(
            document_id="existing-doc",
            status=MapStatus.SUCCESS,
            is_new=False,
        )

        assert doc.status == MapStatus.SUCCESS
        assert doc.is_new is False

    def test_document_with_discovery_url(self):
        """Test MapDocument with discovery_url."""
        doc = MapDocument(
            document_id="doc-with-discovery",
            source_url="https://example.com/page",
            discovery_url="https://example.com/sitemap.xml",
        )

        assert doc.discovery_url == "https://example.com/sitemap.xml"

    def test_document_with_title(self):
        """Test MapDocument with title."""
        doc = MapDocument(
            document_id="titled-doc",
            title="Getting Started Guide",
        )

        assert doc.title == "Getting Started Guide"

    def test_document_with_content_hash(self):
        """Test MapDocument with content_hash for deduplication."""
        doc = MapDocument(
            document_id="file-doc",
            source_type="file",
            content_hash="abc123def456" * 5 + "abcd",  # 64 chars
        )

        assert doc.content_hash == "abc123def456" * 5 + "abcd"
