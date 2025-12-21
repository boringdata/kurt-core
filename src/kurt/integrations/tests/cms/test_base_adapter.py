"""Unit tests for CMS base adapter interface and CMSDocument data class."""

import pytest

from kurt.integrations.cms.base import CMSAdapter, CMSDocument


class TestCMSDocument:
    """Test CMSDocument data class."""

    def test_document_creation_minimal(self):
        """Test creating document with minimal required fields."""
        doc = CMSDocument(
            id="doc-123",
            title="Test Document",
            content="# Hello World\n\nThis is content.",
            content_type="article",
            status="published",
        )

        assert doc.id == "doc-123"
        assert doc.title == "Test Document"
        assert doc.content == "# Hello World\n\nThis is content."
        assert doc.content_type == "article"
        assert doc.status == "published"
        assert doc.url is None
        assert doc.author is None
        assert doc.published_date is None
        assert doc.last_modified is None
        assert doc.metadata is None

    def test_document_creation_full(self):
        """Test creating document with all fields."""
        metadata = {"custom_field": "value", "tags": ["tech", "tutorial"]}
        doc = CMSDocument(
            id="doc-456",
            title="Complete Document",
            content="Full content here",
            content_type="blog_post",
            status="draft",
            url="https://example.com/complete",
            author="John Doe",
            published_date="2024-01-15T10:00:00Z",
            last_modified="2024-01-16T15:30:00Z",
            metadata=metadata,
        )

        assert doc.id == "doc-456"
        assert doc.title == "Complete Document"
        assert doc.url == "https://example.com/complete"
        assert doc.author == "John Doe"
        assert doc.published_date == "2024-01-15T10:00:00Z"
        assert doc.last_modified == "2024-01-16T15:30:00Z"
        assert doc.metadata == metadata
        assert doc.metadata["tags"] == ["tech", "tutorial"]

    def test_to_dict(self):
        """Test converting document to dictionary."""
        doc = CMSDocument(
            id="doc-789",
            title="Dict Test",
            content="Content",
            content_type="page",
            status="published",
            url="https://example.com/dict",
        )

        result = doc.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "doc-789"
        assert result["title"] == "Dict Test"
        assert result["content"] == "Content"
        assert result["content_type"] == "page"
        assert result["status"] == "published"
        assert result["url"] == "https://example.com/dict"

    def test_to_frontmatter_minimal(self):
        """Test converting to frontmatter with minimal fields."""
        doc = CMSDocument(
            id="doc-123",
            title="Frontmatter Test",
            content="Content",
            content_type="article",
            status="published",
        )

        frontmatter = doc.to_frontmatter()

        assert frontmatter["title"] == "Frontmatter Test"
        assert frontmatter["cms_id"] == "doc-123"
        assert frontmatter["cms_type"] == "article"
        assert frontmatter["status"] == "published"
        assert "url" not in frontmatter
        assert "author" not in frontmatter

    def test_to_frontmatter_full(self):
        """Test converting to frontmatter with all fields."""
        metadata = {"category": "tech", "featured": True}
        doc = CMSDocument(
            id="doc-456",
            title="Full Frontmatter",
            content="Content",
            content_type="blog_post",
            status="draft",
            url="https://example.com/post",
            author="Jane Smith",
            published_date="2024-01-15",
            last_modified="2024-01-16",
            metadata=metadata,
        )

        frontmatter = doc.to_frontmatter()

        assert frontmatter["title"] == "Full Frontmatter"
        assert frontmatter["cms_id"] == "doc-456"
        assert frontmatter["cms_type"] == "blog_post"
        assert frontmatter["status"] == "draft"
        assert frontmatter["url"] == "https://example.com/post"
        assert frontmatter["author"] == "Jane Smith"
        assert frontmatter["published_date"] == "2024-01-15"
        assert frontmatter["last_modified"] == "2024-01-16"
        assert frontmatter["cms_metadata"] == metadata
        assert frontmatter["cms_metadata"]["featured"] is True

    def test_status_values(self):
        """Test different status values."""
        statuses = ["draft", "published", "archived", "pending_review"]

        for status in statuses:
            doc = CMSDocument(
                id=f"doc-{status}",
                title=f"Document {status}",
                content="Content",
                content_type="page",
                status=status,
            )
            assert doc.status == status

    def test_content_types(self):
        """Test different content types."""
        content_types = ["article", "blog_post", "page", "product", "tutorial"]

        for ct in content_types:
            doc = CMSDocument(
                id=f"doc-{ct}",
                title=f"Document {ct}",
                content="Content",
                content_type=ct,
                status="published",
            )
            assert doc.content_type == ct


class TestCMSAdapterInterface:
    """Test CMSAdapter abstract interface."""

    def test_adapter_is_abstract(self):
        """Test that CMSAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CMSAdapter(config={})  # Should fail - abstract class

    def test_adapter_must_implement_search(self):
        """Test that subclasses must implement search."""

        class IncompleteAdapter(CMSAdapter):
            def __init__(self, config):
                pass

            def fetch_by_id(self, document_id):
                pass

            def get_content_types(self):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter(config={})  # Should fail - missing search

    def test_adapter_must_implement_fetch_by_id(self):
        """Test that subclasses must implement fetch_by_id."""

        class IncompleteAdapter(CMSAdapter):
            def __init__(self, config):
                pass

            def search(self, query, filters, content_type, limit):
                pass

            def get_content_types(self):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter(config={})  # Should fail - missing fetch_by_id

    def test_adapter_must_implement_get_content_types(self):
        """Test that subclasses must implement get_content_types."""

        class IncompleteAdapter(CMSAdapter):
            def __init__(self, config):
                pass

            def search(self, query, filters, content_type, limit):
                pass

            def fetch_by_id(self, document_id):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter(config={})  # Should fail - missing get_content_types

    def test_adapter_complete_implementation(self):
        """Test that adapter requires all abstract methods."""
        # CMSAdapter has many abstract methods (from sanity impl):
        # search, fetch_by_id, get_content_types, test_connection,
        # list_all, fetch, fetch_batch, create_draft, get_example_document

        # Attempting to create incomplete implementation should fail
        class IncompleteAdapter(CMSAdapter):
            def __init__(self, config):
                self.config = config

            def search(self, query=None, filters=None, content_type=None, limit=100):
                return []

            def fetch_by_id(self, document_id):
                return None

            def get_content_types(self):
                return []

        # Should fail - missing many required abstract methods
        with pytest.raises(TypeError):
            IncompleteAdapter(config={"key": "value"})


class TestCMSDocumentEdgeCases:
    """Test edge cases for CMSDocument."""

    def test_empty_content(self):
        """Test document with empty content."""
        doc = CMSDocument(
            id="doc-empty",
            title="Empty Content",
            content="",
            content_type="page",
            status="draft",
        )

        assert doc.content == ""

    def test_very_long_content(self):
        """Test document with very long content."""
        long_content = "Lorem ipsum " * 10000
        doc = CMSDocument(
            id="doc-long",
            title="Long Content",
            content=long_content,
            content_type="article",
            status="published",
        )

        assert len(doc.content) > 100000

    def test_special_characters_in_fields(self):
        """Test document with special characters."""
        doc = CMSDocument(
            id="doc-special",
            title='Title with "quotes" and special chars: <>&',
            content="Content with émojis 🎉 and unicode: ñ, ü, 中文",
            content_type="page",
            status="published",
            author="Author's Name",
        )

        assert '"quotes"' in doc.title
        assert "🎉" in doc.content
        assert "中文" in doc.content
        assert "Author's Name" == doc.author

    def test_metadata_nested_structure(self):
        """Test document with nested metadata."""
        complex_metadata = {
            "seo": {
                "title": "SEO Title",
                "description": "SEO Description",
                "keywords": ["one", "two"],
            },
            "social": {"twitter": "@handle", "og_image": "image.jpg"},
            "flags": {"featured": True, "pinned": False},
        }

        doc = CMSDocument(
            id="doc-nested",
            title="Nested Metadata",
            content="Content",
            content_type="page",
            status="published",
            metadata=complex_metadata,
        )

        assert doc.metadata["seo"]["keywords"] == ["one", "two"]
        assert doc.metadata["social"]["twitter"] == "@handle"
        assert doc.metadata["flags"]["featured"] is True

        # Verify it survives dict conversion
        doc_dict = doc.to_dict()
        assert doc_dict["metadata"]["seo"]["title"] == "SEO Title"
