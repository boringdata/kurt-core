"""Tests for fetch provider mocks."""

import pytest

from kurt.tools.fetch.core.base import FetchResult
from kurt.tools.fetch.providers.trafilatura.mock import (
    MockTrafilaturaFetcher,
    create_mock as create_trafilatura_mock,
)
from kurt.tools.fetch.providers.httpx.mock import (
    MockHttpxFetcher,
    create_mock as create_httpx_mock,
)
from kurt.tools.fetch.providers.tavily.mock import (
    MockTavilyFetcher,
    create_mock as create_tavily_mock,
)
from kurt.tools.fetch.providers.firecrawl.mock import (
    MockFirecrawlFetcher,
    create_mock as create_firecrawl_mock,
)
from kurt.tools.fetch.providers.apify.mock import (
    MockApifyFetcher,
    create_mock as create_apify_mock,
)
from kurt.tools.fetch.providers.twitterapi.mock import (
    MockTwitterApiFetcher,
    create_mock as create_twitterapi_mock,
)


# ---- Parametrized tests across all fetch mocks ----

ALL_FETCH_MOCKS = [
    ("trafilatura", MockTrafilaturaFetcher, create_trafilatura_mock),
    ("httpx", MockHttpxFetcher, create_httpx_mock),
    ("tavily", MockTavilyFetcher, create_tavily_mock),
    ("firecrawl", MockFirecrawlFetcher, create_firecrawl_mock),
    ("apify", MockApifyFetcher, create_apify_mock),
    ("twitterapi", MockTwitterApiFetcher, create_twitterapi_mock),
]


@pytest.mark.parametrize("name,mock_cls,factory", ALL_FETCH_MOCKS, ids=[m[0] for m in ALL_FETCH_MOCKS])
class TestFetchMockInterface:
    """Verify every fetch mock has the standard interface."""

    def test_provider_metadata(self, name, mock_cls, factory):
        mock = mock_cls()
        assert mock.name == name
        assert mock.version == "mock"
        assert mock.requires_env == []
        assert isinstance(mock.url_patterns, list)

    def test_default_fixture(self, name, mock_cls, factory):
        mock = mock_cls()
        result = mock.fetch("https://example.com/page")
        assert isinstance(result, FetchResult)
        assert result.success is True
        assert result.content  # non-empty

    def test_call_tracking(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.fetch("https://example.com/a")
        mock.fetch("https://example.com/b")
        assert mock.call_count == 2
        assert mock.was_called_with("https://example.com/a")
        assert mock.was_called_with("https://example.com/b")
        assert not mock.was_called_with("https://example.com/c")

    def test_reset(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.fetch("https://example.com/page")
        assert mock.call_count == 1
        mock.reset()
        assert mock.call_count == 0
        assert mock.calls == []

    def test_with_response(self, name, mock_cls, factory):
        mock = mock_cls()
        custom = FetchResult(content="custom content", success=True)
        mock.with_response(custom)
        result = mock.fetch("https://example.com/page")
        assert result.content == "custom content"

    def test_with_error(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.with_error(ConnectionError("Network failure"))
        with pytest.raises(ConnectionError, match="Network failure"):
            mock.fetch("https://example.com/page")
        assert mock.call_count == 1  # call tracked even on error

    def test_with_fixture_success(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.with_fixture("success")
        result = mock.fetch("https://example.com/page")
        assert result.success is True

    def test_with_fixture_error(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.with_fixture("error")
        result = mock.fetch("https://example.com/page")
        assert result.success is False
        assert result.error  # non-empty error message

    def test_with_response_fn(self, name, mock_cls, factory):
        mock = mock_cls()

        def custom_fn(url: str) -> FetchResult:
            return FetchResult(content=f"fetched: {url}", success=True)

        mock.with_response_fn(custom_fn)
        result = mock.fetch("https://example.com/page")
        assert result.content == "fetched: https://example.com/page"

    def test_factory_with_fixture(self, name, mock_cls, factory):
        mock = factory(fixture="success")
        result = mock.fetch("https://example.com/page")
        assert result.success is True

    def test_factory_with_error(self, name, mock_cls, factory):
        mock = factory(error=ValueError("bad"))
        with pytest.raises(ValueError, match="bad"):
            mock.fetch("https://example.com/page")

    def test_factory_with_response(self, name, mock_cls, factory):
        resp = FetchResult(content="factory response", success=True)
        mock = factory(response=resp)
        result = mock.fetch("https://example.com/page")
        assert result.content == "factory response"

    def test_kwargs_passed_through(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.fetch("https://example.com/page", timeout=30, headers={"X-Test": "1"})
        assert mock.calls[0]["timeout"] == 30
        assert mock.calls[0]["headers"] == {"X-Test": "1"}
