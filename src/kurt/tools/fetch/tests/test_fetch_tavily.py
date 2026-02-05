"""Tests for Tavily fetch provider."""

import warnings
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_tavily_singleton():
    """Reset the module-level TavilyFetcher singleton between tests.

    The deprecated tavily.py wrapper uses a lazy singleton pattern.
    Without resetting, tests pollute each other's API key state.
    """
    import kurt.tools.fetch.tavily as tavily_module

    # Reset the singleton before each test
    tavily_module._fetcher = None
    yield
    # Clean up after test
    tavily_module._fetcher = None


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestFetchWithTavily:
    """Test suite for fetch_with_tavily (deprecated wrapper)."""

    def test_import(self):
        """Test that fetch_with_tavily can be imported."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        assert fetch_with_tavily is not None

    def test_empty_urls_returns_empty_dict(self):
        """Test that empty URL list returns empty dict."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        result = fetch_with_tavily([])
        assert result == {}

    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_requires_api_key(self, mock_getenv):
        """Test that tavily raises error without API key."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="TAVILY_API_KEY"):
            fetch_with_tavily("https://example.com")

    def test_max_urls_limit(self):
        """Test that batch fetch raises error for more than 20 URLs."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        urls = [f"https://example{i}.com" for i in range(21)]

        with pytest.raises(ValueError, match="Maximum 20 URLs"):
            fetch_with_tavily(urls)

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_successful_single_url_extraction(self, mock_getenv, mock_client_class):
        """Test successful content extraction for single URL."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "raw_content": "# Example Content\n\nThis is the extracted content.",
                }
            ],
            "response_time": 1.5,
            "request_id": "req-123",
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")

        # Returns BatchFetchResult
        assert "https://example.com" in results
        content, metadata = results["https://example.com"]

        assert content == "# Example Content\n\nThis is the extracted content."
        assert metadata["source_url"] == "https://example.com"
        assert metadata["response_time"] == 1.5
        assert metadata["request_id"] == "req-123"

        # Verify the request was made correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://api.tavily.com/extract"
        assert call_args[1]["json"]["urls"] == "https://example.com"
        assert call_args[1]["json"]["format"] == "markdown"

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_successful_batch_extraction(self, mock_getenv, mock_client_class):
        """Test successful batch content extraction."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        # Mock the HTTP response with multiple results
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example1.com",
                    "raw_content": "# Content 1\n\nFirst page content.",
                },
                {
                    "url": "https://example2.com",
                    "raw_content": "# Content 2\n\nSecond page content.",
                },
            ],
            "response_time": 2.5,
            "request_id": "batch-123",
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily(["https://example1.com", "https://example2.com"])

        assert len(results) == 2
        assert "https://example1.com" in results
        assert "https://example2.com" in results

        content1, metadata1 = results["https://example1.com"]
        assert content1 == "# Content 1\n\nFirst page content."
        assert metadata1["source_url"] == "https://example1.com"
        assert metadata1["response_time"] == 2.5

        content2, metadata2 = results["https://example2.com"]
        assert content2 == "# Content 2\n\nSecond page content."

        # Verify the request was made with array of URLs
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["urls"] == [
            "https://example1.com",
            "https://example2.com",
        ]

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_no_results_returns_failed_urls(self, mock_getenv, mock_client_class):
        """Test that empty results marks URLs as failed."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")

        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "No result" in str(results["https://example.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_empty_content_marked_as_failed(self, mock_getenv, mock_client_class):
        """Test that empty content is marked as failed."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"url": "https://example.com", "raw_content": "   "}]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")

        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "Empty content" in str(results["https://example.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_partial_failure_handling(self, mock_getenv, mock_client_class):
        """Test that partial failures are handled correctly."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://success.com",
                    "raw_content": "# Success\n\nThis worked.",
                },
            ],
            "failed_results": [
                {"url": "https://failed.com", "error": "Access denied"},
            ],
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily(["https://success.com", "https://failed.com"])

        assert len(results) == 2

        # Check success
        content, metadata = results["https://success.com"]
        assert content == "# Success\n\nThis worked."

        # Check failure is an Exception
        assert isinstance(results["https://failed.com"], Exception)
        assert "Access denied" in str(results["https://failed.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_missing_url_marked_as_failed(self, mock_getenv, mock_client_class):
        """Test that URLs not in response are marked as failed."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example1.com",
                    "raw_content": "# Content",
                },
            ],
            "failed_results": [],
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily(["https://example1.com", "https://missing.com"])

        assert len(results) == 2
        assert isinstance(results["https://missing.com"], Exception)
        assert "No result" in str(results["https://missing.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_extracts_favicon_metadata(self, mock_getenv, mock_client_class):
        """Test that favicon is extracted from response."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "raw_content": "# Content",
                    "favicon": "https://example.com/favicon.ico",
                }
            ]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")
        content, metadata = results["https://example.com"]

        assert metadata["favicon"] == "https://example.com/favicon.ico"

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_http_401_returns_invalid_api_key_error(self, mock_getenv, mock_client_class):
        """Test that 401 response returns invalid API key error in results."""
        import httpx

        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 401
        error = httpx.HTTPStatusError("", request=MagicMock(), response=mock_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = error
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")
        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "Invalid API key" in str(results["https://example.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_http_429_returns_rate_limit_error(self, mock_getenv, mock_client_class):
        """Test that 429 response returns rate limit error in results."""
        import httpx

        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError("", request=MagicMock(), response=mock_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = error
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")
        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "Rate limit exceeded" in str(results["https://example.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_http_403_returns_url_not_supported_error(self, mock_getenv, mock_client_class):
        """Test that 403 response returns URL not supported error in results."""
        import httpx

        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 403
        error = httpx.HTTPStatusError("", request=MagicMock(), response=mock_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = error
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")
        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "URL not supported" in str(results["https://example.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_http_432_returns_credit_limit_error(self, mock_getenv, mock_client_class):
        """Test that 432 response returns credit limit error in results."""
        import httpx

        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 432
        error = httpx.HTTPStatusError("", request=MagicMock(), response=mock_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = error
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")
        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "Credit or plan limit exceeded" in str(results["https://example.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_http_500_returns_generic_error(self, mock_getenv, mock_client_class):
        """Test that 500 response returns generic API error in results."""
        import httpx

        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = error
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")
        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "API error (500)" in str(results["https://example.com"])

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_request_error_returns_connection_error(self, mock_getenv, mock_client_class):
        """Test that connection errors are returned in results."""
        import httpx

        from kurt.tools.fetch.tavily import fetch_with_tavily

        mock_getenv.return_value = "test-api-key"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value = mock_client

        results = fetch_with_tavily("https://example.com")
        assert "https://example.com" in results
        assert isinstance(results["https://example.com"], Exception)
        assert "Request error" in str(results["https://example.com"])
        assert "ConnectError" in str(results["https://example.com"])


class TestTavilyFetcher:
    """Test suite for TavilyFetcher engine class."""

    def test_import(self):
        """Test that TavilyFetcher can be imported."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        assert TavilyFetcher is not None

    def test_engine_alias(self):
        """Test that TavilyEngine alias exists for backwards compatibility."""
        from kurt.tools.fetch.engines.tavily import TavilyEngine, TavilyFetcher

        assert TavilyEngine is TavilyFetcher

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_success(self, mock_getenv, mock_client_class):
        """Test successful fetch via TavilyFetcher."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "raw_content": "# Fetched Content\n\nThis is the content.",
                }
            ],
            "response_time": 1.2,
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success is True
        assert result.content == "# Fetched Content\n\nThis is the content."
        assert result.metadata["engine"] == "tavily"
        assert result.error is None

    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_missing_api_key(self, mock_getenv):
        """Test TavilyFetcher returns error when API key missing."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = None

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success is False
        assert "TAVILY_API_KEY" in result.error
        assert result.metadata["engine"] == "tavily"

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_empty_result(self, mock_getenv, mock_client_class):
        """Test TavilyFetcher handles empty results."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success is False
        assert "No result" in result.error

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_with_config(self, mock_getenv, mock_client_class):
        """Test TavilyFetcher accepts config."""
        from kurt.tools.fetch.core.base import FetcherConfig
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"url": "https://example.com", "raw_content": "Content"}]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        config = FetcherConfig(timeout=60.0)
        fetcher = TavilyFetcher(config)

        assert fetcher.config.timeout == 60.0

        result = fetcher.fetch("https://example.com")
        assert result.success is True

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_unexpected_exception(self, mock_getenv, mock_client_class):
        """Test TavilyFetcher handles unexpected exceptions."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        # Make httpx.Client raise an unexpected exception
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = RuntimeError("Unexpected failure")
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        assert result.success is False
        assert "Unexpected error" in result.error
        assert "RuntimeError" in result.error
        assert result.metadata["engine"] == "tavily"

    @patch("kurt.tools.fetch.engines.tavily.httpx.Client")
    @patch("kurt.tools.fetch.engines.tavily.os.getenv")
    def test_fetch_result_is_exception(self, mock_getenv, mock_client_class):
        """Test TavilyFetcher handles Exception objects in results dict."""
        from kurt.tools.fetch.engines.tavily import TavilyFetcher

        mock_getenv.return_value = "test-api-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"url": "https://example.com", "raw_content": ""}],  # Empty content
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = TavilyFetcher()
        result = fetcher.fetch("https://example.com")

        # Empty content is marked as error by fetch_with_tavily
        assert result.success is False
        assert "Empty content" in result.error
