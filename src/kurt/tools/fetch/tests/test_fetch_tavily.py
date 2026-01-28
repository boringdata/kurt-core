"""Tests for Tavily fetch provider."""

from unittest.mock import MagicMock, patch

import pytest


class TestFetchWithTavily:
    """Test suite for fetch_with_tavily."""

    def test_import(self):
        """Test that fetch_with_tavily can be imported."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        assert fetch_with_tavily is not None

    def test_empty_urls_returns_empty_dict(self):
        """Test that empty URL list returns empty dict."""
        from kurt.tools.fetch.tavily import fetch_with_tavily

        result = fetch_with_tavily([])
        assert result == {}

    @patch("kurt.tools.fetch.tavily.os.getenv")
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

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
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

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
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

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
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

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
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

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
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

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
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

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
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

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
    def test_http_401_raises_invalid_api_key(self, mock_getenv, mock_client_class):
        """Test that 401 response raises invalid API key error."""
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

        with pytest.raises(ValueError, match="Invalid API key"):
            fetch_with_tavily("https://example.com")

    @patch("kurt.tools.fetch.tavily.httpx.Client")
    @patch("kurt.tools.fetch.tavily.os.getenv")
    def test_http_429_raises_rate_limit(self, mock_getenv, mock_client_class):
        """Test that 429 response raises rate limit error."""
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

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            fetch_with_tavily("https://example.com")
