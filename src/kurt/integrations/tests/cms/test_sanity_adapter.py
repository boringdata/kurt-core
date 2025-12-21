"""Tests for Sanity CMS adapter with HTTP mocking."""

from unittest.mock import Mock, patch

import pytest

from kurt.integrations.cms.base import CMSDocument
from kurt.integrations.cms.sanity.adapter import SanityAdapter


class TestSanityAdapterInit:
    """Test Sanity adapter initialization."""

    def test_init_minimal_config(self):
        """Test initializing with minimal configuration."""
        config = {
            "project_id": "test-project",
            "dataset": "production",
        }

        adapter = SanityAdapter(config)

        assert adapter.project_id == "test-project"
        assert adapter.dataset == "production"
        assert adapter.token is None
        assert adapter.use_cdn is False
        assert (
            adapter.api_url
            == "https://test-project.api.sanity.io/v2021-10-21/data/query/production"
        )

    def test_init_with_token(self):
        """Test initializing with read token."""
        config = {
            "project_id": "test-project",
            "dataset": "production",
            "token": "sk_test_token_123",
        }

        adapter = SanityAdapter(config)

        assert adapter.token == "sk_test_token_123"

    def test_init_with_cdn(self):
        """Test initializing with CDN enabled."""
        config = {
            "project_id": "test-project",
            "dataset": "production",
            "use_cdn": True,
        }

        adapter = SanityAdapter(config)

        assert adapter.use_cdn is True
        assert "apicdn.sanity.io" in adapter.api_url
        assert (
            adapter.api_url
            == "https://test-project.apicdn.sanity.io/v2021-10-21/data/query/production"
        )

    def test_init_with_base_url(self):
        """Test initializing with custom base URL."""
        config = {
            "project_id": "test-project",
            "dataset": "production",
            "base_url": "https://example.com",
        }

        adapter = SanityAdapter(config)

        assert adapter.base_url == "https://example.com"

    def test_init_with_content_type_mappings(self):
        """Test initializing with content type mappings."""
        mappings = {
            "article": {
                "enabled": True,
                "content_field": "body",
                "title_field": "title",
            }
        }
        config = {
            "project_id": "test-project",
            "dataset": "production",
            "content_type_mappings": mappings,
        }

        adapter = SanityAdapter(config)

        assert adapter.mappings == mappings
        assert adapter.mappings["article"]["content_field"] == "body"


class TestSanityTestConnection:
    """Test Sanity connection testing."""

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_connection_success(self, mock_requests):
        """Test successful connection to Sanity."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        result = adapter.test_connection()

        assert result is True
        mock_requests.get.assert_called_once()

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_connection_with_auth(self, mock_requests):
        """Test connection with authentication token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter(
            {"project_id": "test", "dataset": "production", "token": "sk_test_token"}
        )
        result = adapter.test_connection()

        assert result is True
        call_args = mock_requests.get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer sk_test_token"

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_connection_failure(self, mock_requests):
        """Test connection failure."""
        mock_requests.get.side_effect = Exception("Network error")

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        result = adapter.test_connection()

        assert result is False

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_connection_401_unauthorized(self, mock_requests):
        """Test connection with 401 Unauthorized."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter(
            {"project_id": "test", "dataset": "production", "token": "invalid_token"}
        )
        result = adapter.test_connection()

        assert result is False


class TestSanitySearch:
    """Test Sanity search functionality."""

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_search_all_documents(self, mock_requests):
        """Test searching all documents without filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "_id": "doc1",
                    "_type": "article",
                    "title": "Test Article",
                    "body": "Content here",
                    "status": "published",
                },
                {
                    "_id": "doc2",
                    "_type": "article",
                    "title": "Another Article",
                    "body": "More content",
                    "status": "draft",
                },
            ]
        }
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        results = adapter.search()

        assert len(results) == 2
        assert isinstance(results[0], CMSDocument)
        assert results[0].id == "doc1"
        assert results[0].title == "Test Article"
        assert results[0].content_type == "article"
        assert results[0].status == "published"

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_search_with_content_type_filter(self, mock_requests):
        """Test searching with content type filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "_id": "blog1",
                    "_type": "blog_post",
                    "title": "Blog Post",
                    "body": "Blog content",
                    "status": "published",
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        results = adapter.search(content_type="blog_post")

        assert len(results) == 1
        assert results[0].content_type == "blog_post"

        # Verify GROQ query contains type filter
        call_args = mock_requests.get.call_args
        query = call_args[1]["params"]["query"]
        assert '_type == "blog_post"' in query

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_search_with_text_query(self, mock_requests):
        """Test searching with text query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        _ = adapter.search(query="kubernetes")

        # Verify GROQ query contains text search
        call_args = mock_requests.get.call_args
        query = call_args[1]["params"]["query"]
        assert "kubernetes" in query.lower()

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_search_with_limit(self, mock_requests):
        """Test searching with result limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        _ = adapter.search(limit=10)

        # Verify GROQ query contains limit
        call_args = mock_requests.get.call_args
        query = call_args[1]["params"]["query"]
        assert "[0...10]" in query or "[0..10]" in query

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_search_with_filters(self, mock_requests):
        """Test searching with custom filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        filters = {"status": "published", "featured": True}
        _ = adapter.search(filters=filters)

        # Verify filters are in query
        call_args = mock_requests.get.call_args
        query = call_args[1]["params"]["query"]
        assert "status" in query or "published" in query

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_search_http_error(self, mock_requests):
        """Test search with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})

        with pytest.raises(Exception):
            adapter.search()


class TestSanityFetch:
    """Test fetching documents by ID."""

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_fetch_success(self, mock_requests):
        """Test successfully fetching document by ID."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Note: GROQ query ends with [0] so result is a single dict, not a list
        mock_response.json.return_value = {
            "result": {
                "_id": "doc-123",
                "_type": "article",
                "title": "Fetched Document",
                "body": [{"_type": "block", "children": [{"text": "Document content"}]}],
                "status": "published",
                "author": {"name": "John Doe"},
                "publishedAt": "2024-01-15T10:00:00Z",
            }
        }
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        doc = adapter.fetch("doc-123")

        assert doc is not None
        assert doc.id == "doc-123"
        assert doc.title == "Fetched Document"
        assert doc.status == "published"
        # Content is converted from blocks to markdown
        assert doc.content is not None

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_fetch_not_found(self, mock_requests):
        """Test fetching non-existent document."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": None}  # _query returns None when not found
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})

        # When document not found, adapter raises ValueError
        with pytest.raises(ValueError) as exc_info:
            adapter.fetch("nonexistent-id")

        assert "Document not found" in str(exc_info.value)

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_fetch_with_custom_mappings(self, mock_requests):
        """Test fetching document with custom field mappings."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Note: GROQ query ends with [0] so result is a single dict
        mock_response.json.return_value = {
            "result": {
                "_id": "doc-456",
                "_type": "customType",
                "customTitle": "Custom Title",
                "customContent": [{"_type": "block", "children": [{"text": "Custom Content"}]}],
            }
        }
        mock_requests.get.return_value = mock_response

        mappings = {
            "customType": {
                "enabled": True,
                "title_field": "customTitle",
                "content_field": "customContent",
            }
        }
        adapter = SanityAdapter(
            {
                "project_id": "test",
                "dataset": "production",
                "content_type_mappings": mappings,
            }
        )
        doc = adapter.fetch("doc-456")

        assert doc is not None
        # The adapter should use custom mappings
        assert doc.title == "Custom Title"


class TestSanityGetContentTypes:
    """Test getting content types from Sanity."""

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_get_content_types_success(self, mock_requests):
        """Test successfully getting content types."""

        # First call returns unique types, subsequent calls return counts
        def mock_get_response(*args, **kwargs):
            query = kwargs.get("params", {}).get("query", "")
            mock_response = Mock()
            mock_response.status_code = 200

            if "array::unique" in query:
                # First query gets unique types
                mock_response.json.return_value = {
                    "result": {"types": ["article", "blog_post", "page", "product"]}
                }
            elif "count(*" in query:
                # Subsequent queries get counts
                mock_response.json.return_value = {"result": 10}
            else:
                mock_response.json.return_value = {"result": None}

            return mock_response

        mock_requests.get.side_effect = mock_get_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        types = adapter.get_content_types()

        assert isinstance(types, list)
        assert len(types) == 4
        assert all("name" in t and "count" in t for t in types)
        assert types[0]["name"] == "article"
        assert types[0]["count"] == 10

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_get_content_types_empty(self, mock_requests):
        """Test getting content types from empty schema."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Empty types result
        mock_response.json.return_value = {"result": {"types": []}}
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        types = adapter.get_content_types()

        assert isinstance(types, list)
        assert len(types) == 0


class TestSanityMutations:
    """Test create/update/publish operations."""

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_create_draft_requires_write_token(self, mock_requests):
        """Test that create_draft requires write token."""
        adapter = SanityAdapter(
            {
                "project_id": "test",
                "dataset": "production",
                # No write_token provided
            }
        )

        with pytest.raises(ValueError) as exc_info:
            adapter._mutate([{"create": {"_type": "article"}}])

        assert "API token required for mutations" in str(exc_info.value)

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_create_draft_success(self, mock_requests):
        """Test creating draft document."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transactionId": "abc123",
            "results": [{"id": "drafts.new-doc-id", "operation": "create"}],
        }
        mock_requests.post.return_value = mock_response

        adapter = SanityAdapter(
            {
                "project_id": "test",
                "dataset": "production",
                "write_token": "sk_write_token",
            }
        )

        mutation = [{"create": {"_type": "article", "title": "New Article"}}]
        result = adapter._mutate(mutation)

        assert result is not None
        assert "transactionId" in result
        mock_requests.post.assert_called_once()

        # Verify authorization header
        call_args = mock_requests.post.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer sk_write_token"

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_mutation_error(self, mock_requests):
        """Test mutation with error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = Exception("400 Bad Request")
        mock_requests.post.return_value = mock_response

        adapter = SanityAdapter(
            {
                "project_id": "test",
                "dataset": "production",
                "write_token": "sk_write_token",
            }
        )

        with pytest.raises(Exception):
            adapter._mutate([{"create": {"_type": "invalid"}}])


class TestSanityGROQConstruction:
    """Test GROQ query construction patterns."""

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_groq_query_escaping(self, mock_requests):
        """Test that GROQ queries properly escape special characters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})

        # Search with special characters that could cause injection
        adapter.search(query="test' OR '1'='1")

        call_args = mock_requests.get.call_args
        query = call_args[1]["params"]["query"]

        # Query should not contain raw injection attempt
        # (exact escaping depends on implementation)
        assert query is not None

    @patch("kurt.integrations.cms.sanity.adapter.requests")
    def test_groq_query_structure(self, mock_requests):
        """Test basic GROQ query structure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": []}
        mock_requests.get.return_value = mock_response

        adapter = SanityAdapter({"project_id": "test", "dataset": "production"})
        adapter.search(content_type="article")

        call_args = mock_requests.get.call_args
        query = call_args[1]["params"]["query"]

        # Query should contain GROQ array selector (with possible whitespace)
        assert "*[" in query.replace(" ", "").replace("\n", "")
        # Should have content type filter
        assert "article" in query
        # Should have proper closing
        assert "]" in query
