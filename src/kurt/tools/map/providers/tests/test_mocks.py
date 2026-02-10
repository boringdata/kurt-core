"""Tests for map provider mocks."""

import pytest

from kurt.tools.map.core.base import MapperResult
from kurt.tools.map.providers.apify.mock import (
    MockApifyMapper,
)
from kurt.tools.map.providers.apify.mock import (
    create_mock as create_apify_mock,
)
from kurt.tools.map.providers.cms.mock import (
    MockCmsMapper,
)
from kurt.tools.map.providers.cms.mock import (
    create_mock as create_cms_mock,
)
from kurt.tools.map.providers.crawl.mock import (
    MockCrawlMapper,
)
from kurt.tools.map.providers.crawl.mock import (
    create_mock as create_crawl_mock,
)
from kurt.tools.map.providers.folder.mock import (
    MockFolderMapper,
)
from kurt.tools.map.providers.folder.mock import (
    create_mock as create_folder_mock,
)
from kurt.tools.map.providers.rss.mock import (
    MockRssMapper,
)
from kurt.tools.map.providers.rss.mock import (
    create_mock as create_rss_mock,
)
from kurt.tools.map.providers.sitemap.mock import (
    MockSitemapMapper,
)
from kurt.tools.map.providers.sitemap.mock import (
    create_mock as create_sitemap_mock,
)

# ---- Parametrized tests across all map mocks ----

ALL_MAP_MOCKS = [
    ("sitemap", MockSitemapMapper, create_sitemap_mock),
    ("rss", MockRssMapper, create_rss_mock),
    ("crawl", MockCrawlMapper, create_crawl_mock),
    ("cms", MockCmsMapper, create_cms_mock),
    ("folder", MockFolderMapper, create_folder_mock),
    ("apify", MockApifyMapper, create_apify_mock),
]


@pytest.mark.parametrize("name,mock_cls,factory", ALL_MAP_MOCKS, ids=[m[0] for m in ALL_MAP_MOCKS])
class TestMapMockInterface:
    """Verify every map mock has the standard interface."""

    def test_provider_metadata(self, name, mock_cls, factory):
        mock = mock_cls()
        assert mock.name == name
        assert mock.version == "mock"
        assert mock.requires_env == []
        assert isinstance(mock.url_patterns, list)

    def test_default_fixture(self, name, mock_cls, factory):
        mock = mock_cls()
        result = mock.map("https://example.com/sitemap.xml")
        assert isinstance(result, MapperResult)
        assert isinstance(result.urls, list)
        assert len(result.urls) > 0

    def test_call_tracking(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.map("https://example.com/a")
        mock.map("https://example.com/b")
        assert mock.call_count == 2
        assert mock.was_called_with("https://example.com/a")
        assert mock.was_called_with("https://example.com/b")
        assert not mock.was_called_with("https://example.com/c")

    def test_reset(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.map("https://example.com/sitemap.xml")
        assert mock.call_count == 1
        mock.reset()
        assert mock.call_count == 0
        assert mock.calls == []

    def test_with_response(self, name, mock_cls, factory):
        mock = mock_cls()
        custom = MapperResult(urls=["https://custom.com/page"], count=1)
        mock.with_response(custom)
        result = mock.map("https://example.com/sitemap.xml")
        assert result.urls == ["https://custom.com/page"]

    def test_with_error(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.with_error(ConnectionError("Network failure"))
        with pytest.raises(ConnectionError, match="Network failure"):
            mock.map("https://example.com/sitemap.xml")
        assert mock.call_count == 1

    def test_with_fixture_success(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.with_fixture("success")
        result = mock.map("https://example.com/sitemap.xml")
        assert len(result.urls) > 0

    def test_with_fixture_error(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.with_fixture("error")
        result = mock.map("https://example.com/sitemap.xml")
        assert result.urls == []
        assert len(result.errors) > 0

    def test_with_response_fn(self, name, mock_cls, factory):
        mock = mock_cls()

        def custom_fn(source: str) -> MapperResult:
            return MapperResult(urls=[f"{source}/page-1"], count=1)

        mock.with_response_fn(custom_fn)
        result = mock.map("https://example.com")
        assert result.urls == ["https://example.com/page-1"]

    def test_with_urls(self, name, mock_cls, factory):
        mock = mock_cls()
        urls = ["https://example.com/a", "https://example.com/b"]
        mock.with_urls(urls)
        result = mock.map("https://example.com/sitemap.xml")
        assert result.urls == urls
        assert result.count == 2

    def test_factory_with_fixture(self, name, mock_cls, factory):
        mock = factory(fixture="success")
        result = mock.map("https://example.com/sitemap.xml")
        assert len(result.urls) > 0

    def test_factory_with_error(self, name, mock_cls, factory):
        mock = factory(error=ValueError("bad"))
        with pytest.raises(ValueError, match="bad"):
            mock.map("https://example.com/sitemap.xml")

    def test_factory_with_urls(self, name, mock_cls, factory):
        mock = factory(urls=["https://example.com/page"])
        result = mock.map("https://example.com/sitemap.xml")
        assert result.urls == ["https://example.com/page"]

    def test_kwargs_passed_through(self, name, mock_cls, factory):
        mock = mock_cls()
        mock.map("https://example.com/sitemap.xml", depth=3, follow_external=True)
        assert mock.calls[0]["depth"] == 3
        assert mock.calls[0]["follow_external"] is True
