"""Tests for the Apify client."""

import os
from unittest.mock import MagicMock, patch

import pytest

from kurt.integrations.apify.client import (
    ApifyActorError,
    ApifyAuthError,
    ApifyClient,
    ApifyTimeoutError,
    run_actor,
)


class TestApifyClientInit:
    """Test ApifyClient initialization."""

    def test_requires_api_key(self):
        """Test that ApifyClient raises error when no API key provided."""
        with patch.dict(os.environ, {}, clear=True):
            if "APIFY_API_KEY" in os.environ:
                del os.environ["APIFY_API_KEY"]
            with pytest.raises(ApifyAuthError, match="Apify API key required"):
                ApifyClient()

    def test_uses_provided_api_key(self):
        """Test that ApifyClient uses provided API key."""
        client = ApifyClient(api_key="test_key")
        assert client.api_key == "test_key"

    def test_uses_env_var_api_key(self):
        """Test that ApifyClient uses APIFY_API_KEY env var."""
        with patch.dict(os.environ, {"APIFY_API_KEY": "env_key"}):
            client = ApifyClient()
            assert client.api_key == "env_key"

    def test_default_timeout(self):
        """Test default timeout value."""
        client = ApifyClient(api_key="test_key")
        assert client.timeout == 120.0

    def test_custom_timeout(self):
        """Test custom timeout value."""
        client = ApifyClient(api_key="test_key", timeout=60.0)
        assert client.timeout == 60.0


class TestApifyClientConnection:
    """Test ApifyClient connection methods."""

    def test_test_connection_success(self):
        """Test successful connection test."""
        with patch.object(ApifyClient, "client", new_callable=lambda: MagicMock()) as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_http.get.return_value = mock_response

            client = ApifyClient(api_key="test_key")
            client._client = mock_http
            assert client.test_connection() is True

    def test_test_connection_failure(self):
        """Test failed connection test."""
        import httpx

        with patch.object(ApifyClient, "client", new_callable=lambda: MagicMock()) as mock_http:
            mock_http.get.side_effect = httpx.RequestError("Connection failed")

            client = ApifyClient(api_key="test_key")
            client._client = mock_http
            assert client.test_connection() is False

    def test_get_user_info_success(self):
        """Test successful user info retrieval."""
        with patch.object(ApifyClient, "client", new_callable=lambda: MagicMock()) as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "user123", "username": "testuser"}
            mock_http.get.return_value = mock_response

            client = ApifyClient(api_key="test_key")
            client._client = mock_http
            user_info = client.get_user_info()
            assert user_info["id"] == "user123"


class TestApifyClientRunActor:
    """Test ApifyClient.run_actor method."""

    def test_run_actor_success(self):
        """Test successful actor run."""
        with patch.object(ApifyClient, "client", new_callable=lambda: MagicMock()) as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"id": "1", "text": "content"}]
            mock_response.raise_for_status = MagicMock()
            mock_http.post.return_value = mock_response

            client = ApifyClient(api_key="test_key")
            client._client = mock_http
            result = client.run_actor("apidojo/tweet-scraper", {"searchTerms": ["AI"]})

            assert len(result) == 1
            assert result[0]["text"] == "content"

    def test_run_actor_auth_error(self):
        """Test actor run with auth error."""
        with patch.object(ApifyClient, "client", new_callable=lambda: MagicMock()) as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_http.post.return_value = mock_response

            client = ApifyClient(api_key="test_key")
            client._client = mock_http

            with pytest.raises(ApifyAuthError, match="Invalid Apify API key"):
                client.run_actor("apidojo/tweet-scraper", {"searchTerms": ["AI"]})

    def test_run_actor_not_found(self):
        """Test actor run with actor not found error."""
        with patch.object(ApifyClient, "client", new_callable=lambda: MagicMock()) as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_http.post.return_value = mock_response

            client = ApifyClient(api_key="test_key")
            client._client = mock_http

            with pytest.raises(ApifyActorError, match="Actor not found"):
                client.run_actor("nonexistent/actor", {})

    def test_run_actor_timeout(self):
        """Test actor run with timeout."""
        import httpx

        with patch.object(ApifyClient, "client", new_callable=lambda: MagicMock()) as mock_http:
            mock_http.post.side_effect = httpx.TimeoutException("Request timed out")

            client = ApifyClient(api_key="test_key")
            client._client = mock_http

            with pytest.raises(ApifyTimeoutError):
                client.run_actor("apidojo/tweet-scraper", {}, timeout=1.0)


class TestApifyClientFetch:
    """Test ApifyClient.fetch method."""

    def test_fetch_with_platform(self):
        """Test fetch with platform parameter."""
        client = ApifyClient(api_key="test_key")

        with patch.object(client, "run_actor") as mock_run:
            mock_run.return_value = [{"text": "content", "url": "https://twitter.com/post/1"}]

            result = client.fetch("AI agents", platform="twitter", max_items=10)

            assert len(result) == 1
            assert result[0].text == "content"
            mock_run.assert_called_once()

    def test_fetch_with_actor_id(self):
        """Test fetch with explicit actor_id."""
        client = ApifyClient(api_key="test_key")

        with patch.object(client, "run_actor") as mock_run:
            mock_run.return_value = [{"text": "content", "url": "https://example.com"}]

            result = client.fetch("query", actor_id="custom/actor", max_items=10)

            assert len(result) == 1
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == "custom/actor"

    def test_fetch_requires_platform_or_actor(self):
        """Test that fetch requires either platform or actor_id."""
        client = ApifyClient(api_key="test_key")

        with pytest.raises(ValueError, match="Must specify either actor_id or platform"):
            client.fetch("query")

    def test_fetch_unknown_platform(self):
        """Test fetch with unknown platform."""
        client = ApifyClient(api_key="test_key")

        with pytest.raises(ValueError, match="Unknown platform"):
            client.fetch("query", platform="unknown_platform")


class TestApifyClientContextManager:
    """Test ApifyClient as context manager."""

    def test_context_manager(self):
        """Test client as context manager."""
        with ApifyClient(api_key="test_key") as client:
            assert client.api_key == "test_key"

    def test_close(self):
        """Test client close method."""
        client = ApifyClient(api_key="test_key")
        # Access client property to initialize httpx client
        _ = client.client
        assert client._client is not None
        client.close()
        assert client._client is None


class TestRunActorFunction:
    """Test the run_actor convenience function."""

    def test_run_actor_function(self):
        """Test run_actor convenience function."""
        with patch("kurt.integrations.apify.client.ApifyClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.run_actor.return_value = [{"text": "content"}]
            mock_client_class.return_value.__enter__.return_value = mock_instance

            result = run_actor(
                "apidojo/tweet-scraper",
                {"searchTerms": ["AI"]},
                api_key="test_key",
            )

            assert result == [{"text": "content"}]


class TestApifyClientHighLevel:
    """Test high-level convenience methods."""

    def test_search_twitter(self):
        """Test search_twitter convenience method."""
        client = ApifyClient(api_key="test_key")

        with patch.object(client, "fetch") as mock_fetch:
            mock_fetch.return_value = []
            client.search_twitter("AI agents", max_items=10)

            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args[1]
            assert call_kwargs["platform"] == "twitter"
            assert call_kwargs["max_items"] == 10

    def test_search_linkedin(self):
        """Test search_linkedin convenience method."""
        client = ApifyClient(api_key="test_key")

        with patch.object(client, "fetch") as mock_fetch:
            mock_fetch.return_value = []
            client.search_linkedin("data engineering", max_items=20)

            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args[1]
            assert call_kwargs["platform"] == "linkedin"
            assert call_kwargs["max_items"] == 20

    def test_search_substack(self):
        """Test search_substack convenience method."""
        client = ApifyClient(api_key="test_key")

        with patch.object(client, "fetch") as mock_fetch:
            mock_fetch.return_value = []
            client.search_substack("machine learning", max_items=15)

            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args[1]
            assert call_kwargs["platform"] == "substack"

    def test_fetch_profile(self):
        """Test fetch_profile method."""
        client = ApifyClient(api_key="test_key")

        with patch.object(client, "fetch") as mock_fetch:
            mock_fetch.return_value = []
            client.fetch_profile("@username", platform="twitter", max_items=50)

            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args[1]
            # fetch_profile should use profile-specific actor
            assert "actor_id" in call_kwargs
