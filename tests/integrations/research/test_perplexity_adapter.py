"""Tests for Perplexity research adapter with HTTP mocking."""

from unittest.mock import Mock, patch

import pytest

from kurt.integrations.research.base import ResearchResult
from kurt.integrations.research.perplexity.adapter import PerplexityAdapter


class TestPerplexityAdapterInit:
    """Test Perplexity adapter initialization."""

    def test_init_minimal_config(self):
        """Test initializing with minimal configuration."""
        config = {"api_key": "pplx_test_key_123"}

        adapter = PerplexityAdapter(config)

        assert adapter.api_key == "pplx_test_key_123"
        assert adapter.default_model == "sonar-reasoning"
        assert adapter.default_recency == "day"
        assert adapter.max_tokens == 4000
        assert adapter.temperature == 0.2

    def test_init_with_custom_settings(self):
        """Test initializing with custom settings."""
        config = {
            "api_key": "pplx_custom_key",
            "default_model": "sonar-pro",
            "default_recency": "week",
            "max_tokens": 8000,
            "temperature": 0.5,
        }

        adapter = PerplexityAdapter(config)

        assert adapter.api_key == "pplx_custom_key"
        assert adapter.default_model == "sonar-pro"
        assert adapter.default_recency == "week"
        assert adapter.max_tokens == 8000
        assert adapter.temperature == 0.5

    def test_api_url_constant(self):
        """Test that API URL is correctly set."""
        assert PerplexityAdapter.API_URL == "https://api.perplexity.ai/chat/completions"


class TestPerplexityTestConnection:
    """Test Perplexity connection testing."""

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_connection_success(self, mock_requests):
        """Test successful connection to Perplexity."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test response"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.test_connection()

        assert result is True
        mock_requests.post.assert_called_once()

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_connection_failure(self, mock_requests):
        """Test connection failure."""
        mock_requests.post.side_effect = Exception("Network error")

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.test_connection()

        assert result is False

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_connection_401_unauthorized(self, mock_requests):
        """Test connection with 401 Unauthorized."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "invalid_key"})
        result = adapter.test_connection()

        assert result is False


class TestPerplexitySearch:
    """Test Perplexity search functionality."""

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_basic_query(self, mock_requests):
        """Test basic search query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Kubernetes is an open-source container orchestration platform [1][2]."
                    }
                }
            ],
            "citations": [
                "https://kubernetes.io/docs",
                "https://www.cncf.io/projects/kubernetes/",
            ],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("What is Kubernetes?")

        assert isinstance(result, ResearchResult)
        assert result.query == "What is Kubernetes?"
        assert "Kubernetes" in result.answer
        assert len(result.citations) == 2
        assert result.source == "perplexity"
        assert result.citations[0].url == "https://kubernetes.io/docs"
        assert result.citations[1].url == "https://www.cncf.io/projects/kubernetes/"

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_with_recency_filter(self, mock_requests):
        """Test search with recency filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Recent news about AI..."}}],
            "citations": ["https://techcrunch.com/ai-news"],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("AI news", recency="hour")

        assert result.query == "AI news"
        assert result.metadata["recency"] == "hour"

        # Verify request payload
        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]
        assert payload["search_recency_filter"] == "hour"

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_with_custom_model(self, mock_requests):
        """Test search with custom model."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Answer from sonar-pro"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("test query", model="sonar-pro")

        assert result.model == "sonar-pro"

        # Verify request payload
        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]
        assert payload["model"] == "sonar-pro"

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_with_domain_filter(self, mock_requests):
        """Test search with domain filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Results from docs.github.com"}}],
            "citations": ["https://docs.github.com/en/actions"],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("GitHub Actions", domains=["docs.github.com"])

        assert "docs.github.com" in result.citations[0].url

        # Verify request payload
        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]
        assert payload["search_domain_filter"] == ["docs.github.com"]

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_with_no_citations(self, mock_requests):
        """Test search when no citations are returned."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Answer without external sources"}}],
            # No citations field
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("general knowledge query")

        assert len(result.citations) == 0

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_http_error(self, mock_requests):
        """Test search with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})

        with pytest.raises(Exception):
            adapter.search("test query")

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_rate_limit_error(self, mock_requests):
        """Test search with rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = Exception("429 Too Many Requests")
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})

        with pytest.raises(Exception):
            adapter.search("test query")


class TestPerplexityRequestFormatting:
    """Test request formatting and payload construction."""

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_request_headers(self, mock_requests):
        """Test that request headers are correctly formatted."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_api_key_123"})
        adapter.search("test")

        call_args = mock_requests.post.call_args
        headers = call_args[1]["headers"]

        assert headers["Authorization"] == "Bearer test_api_key_123"
        assert headers["Content-Type"] == "application/json"

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_request_system_message(self, mock_requests):
        """Test that system message is included in payload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        adapter.search("test query")

        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]

        messages = payload["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "research assistant" in messages[0]["content"].lower()
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "test query"

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_request_parameters(self, mock_requests):
        """Test that request parameters are correctly set."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key", "max_tokens": 8000, "temperature": 0.7})
        adapter.search("test")

        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]

        assert payload["max_tokens"] == 8000
        assert payload["temperature"] == 0.7
        assert payload["return_citations"] is True
        assert payload["return_images"] is False

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_recency_filter_mapping(self, mock_requests):
        """Test that recency filter values are correctly mapped."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})

        recency_tests = {
            "hour": "hour",
            "day": "day",
            "week": "week",
            "month": "month",
            None: "day",  # default
        }

        for input_recency, expected_filter in recency_tests.items():
            adapter.search("test", recency=input_recency)

            call_args = mock_requests.post.call_args
            payload = call_args[1]["json"]

            assert payload["search_recency_filter"] == expected_filter


class TestPerplexityResponseParsing:
    """Test response parsing and result construction."""

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_result_id_format(self, mock_requests):
        """Test that result IDs are correctly formatted."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test answer"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("test")

        # ID format: res_YYYYMMDD_xxxxxxxx
        assert result.id.startswith("res_")
        assert len(result.id) == 21  # res_ + 8 digits + _ + 8 hex chars

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_citation_domain_extraction(self, mock_requests):
        """Test that domains are extracted from citation URLs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [
                "https://docs.python.org/3/library/",
                "https://www.github.com/python/cpython",
            ],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("test")

        assert result.citations[0].domain == "docs.python.org"
        assert result.citations[1].domain == "www.github.com"

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    @patch("kurt.integrations.research.perplexity.adapter.time")
    def test_response_time_tracking(self, mock_time, mock_requests):
        """Test that response time is accurately tracked."""
        # Mock time.time() to return specific values
        mock_time.time.side_effect = [100.0, 102.5]  # 2.5 second response

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("test")

        assert result.response_time_seconds == 2.5

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_citation_title_numbering(self, mock_requests):
        """Test that citations are numbered correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        result = adapter.search("test")

        assert result.citations[0].title == "Source 1"
        assert result.citations[1].title == "Source 2"
        assert result.citations[2].title == "Source 3"

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_metadata_fields(self, mock_requests):
        """Test that metadata fields are correctly populated."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key", "default_model": "sonar-reasoning"})
        result = adapter.search("test", recency="week")

        assert result.metadata["recency"] == "week"
        assert result.metadata["model"] == "sonar-reasoning"
        assert result.timestamp is not None


class TestPerplexityEdgeCases:
    """Test edge cases and error handling."""

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_with_special_characters(self, mock_requests):
        """Test search with special characters in query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test answer"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        query = 'How to use "quotes" & special <chars> in Python?'
        result = adapter.search(query)

        assert result.query == query

        # Verify query is correctly included in request
        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]
        assert payload["messages"][1]["content"] == query

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_with_very_long_query(self, mock_requests):
        """Test search with very long query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test answer"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        long_query = "What is " + "very " * 100 + "long query?"
        result = adapter.search(long_query)

        assert result.query == long_query
        assert len(result.query) > 500

    @patch("kurt.integrations.research.perplexity.adapter.requests")
    def test_search_timeout(self, mock_requests):
        """Test that search has appropriate timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}],
            "citations": [],
        }
        mock_requests.post.return_value = mock_response

        adapter = PerplexityAdapter({"api_key": "test_key"})
        adapter.search("test")

        call_args = mock_requests.post.call_args
        assert call_args[1]["timeout"] == 120  # 2 minute timeout

    def test_extract_domain_valid_url(self):
        """Test domain extraction from valid URLs."""
        adapter = PerplexityAdapter({"api_key": "test_key"})

        assert adapter._extract_domain("https://docs.python.org/3/") == "docs.python.org"
        assert adapter._extract_domain("http://example.com/path") == "example.com"
        assert adapter._extract_domain("https://subdomain.example.com") == "subdomain.example.com"

    def test_extract_domain_invalid_url(self):
        """Test domain extraction from invalid URLs."""
        adapter = PerplexityAdapter({"api_key": "test_key"})

        # Should return empty string for invalid URLs (netloc is empty)
        assert adapter._extract_domain("not a url") == ""
        assert adapter._extract_domain("") == ""
