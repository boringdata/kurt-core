"""Tests for Phase 4-5 subcommands."""

import pytest
from datetime import datetime

from kurt.tools.map.subcommands import (
    MapDocSubcommand,
    MapProfileSubcommand,
    MapPostsSubcommand,
)
from kurt.tools.fetch.subcommands import (
    FetchDocSubcommand,
    FetchProfileSubcommand,
    FetchPostsSubcommand,
)
from kurt.tools.map.core import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.models import DocType
from kurt.tools.fetch.core import BaseFetcher, FetchResult


class MockMapper(BaseMapper):
    """Mock mapper for testing."""

    def map(self, source: str, doc_type: DocType = DocType.DOC) -> MapperResult:
        """Mock map implementation."""
        return MapperResult(
            urls=[
                f"{source}/page1",
                f"{source}/page2",
                f"{source}/page3",
            ],
            count=3,
        )


class MockFetcher(BaseFetcher):
    """Mock fetcher for testing."""

    def fetch(self, url: str) -> FetchResult:
        """Mock fetch implementation."""
        return FetchResult(
            content=f"Content from {url}",
            content_html=f"<p>Content from {url}</p>",
        )


class TestMapDocSubcommand:
    """Test map doc subcommand."""

    def test_map_doc_basic(self):
        """Test basic doc mapping."""
        mapper = MockMapper()
        cmd = MapDocSubcommand(mapper)
        results = cmd.run("https://example.com")

        assert len(results) == 3
        assert all(r.url.startswith("https://example.com") for r in results)

    def test_map_doc_with_depth(self):
        """Test doc mapping with depth."""
        mapper = MockMapper()
        cmd = MapDocSubcommand(mapper)
        results = cmd.run("https://example.com", depth=5)

        assert len(results) == 3
        assert mapper.config.max_depth == 5

    def test_map_doc_with_patterns(self):
        """Test doc mapping with patterns."""
        mapper = MockMapper()
        cmd = MapDocSubcommand(mapper)
        results = cmd.run(
            "https://example.com",
            include_pattern=r".*blog.*",
            exclude_pattern=r".*admin.*",
        )

        assert len(results) == 3
        assert mapper.config.include_pattern == r".*blog.*"
        assert mapper.config.exclude_pattern == r".*admin.*"


class TestMapProfileSubcommand:
    """Test map profile subcommand."""

    def test_map_profile_basic(self):
        """Test basic profile mapping."""
        mapper = MockMapper()
        cmd = MapProfileSubcommand(mapper)
        results = cmd.run("AI", platform="twitter")

        assert len(results) == 3
        assert all(r.platform == "twitter" for r in results)

    def test_map_profile_with_limit(self):
        """Test profile mapping with limit."""
        mapper = MockMapper()
        cmd = MapProfileSubcommand(mapper)
        results = cmd.run("startup", platform="linkedin", limit=50)

        assert len(results) <= 50
        assert mapper.config.max_urls == 50

    def test_map_profile_different_platforms(self):
        """Test profiles on different platforms."""
        mapper = MockMapper()

        for platform in ["twitter", "linkedin", "instagram"]:
            cmd = MapProfileSubcommand(mapper)
            results = cmd.run("query", platform=platform)

            assert all(r.platform == platform for r in results)


class TestMapPostsSubcommand:
    """Test map posts subcommand."""

    def test_map_posts_basic(self):
        """Test basic posts mapping."""
        mapper = MockMapper()
        cmd = MapPostsSubcommand(mapper)
        results = cmd.run("https://twitter.com/user")

        assert len(results) == 3
        assert all(r.published_at is not None for r in results)

    def test_map_posts_with_limit(self):
        """Test posts mapping with limit."""
        mapper = MockMapper()
        cmd = MapPostsSubcommand(mapper)
        results = cmd.run("hashtag", limit=20)

        assert len(results) <= 20
        assert mapper.config.max_urls == 20

    def test_map_posts_with_date_filter(self):
        """Test posts mapping with date filter."""
        mapper = MockMapper()
        cmd = MapPostsSubcommand(mapper)
        results = cmd.run("query", since="2024-01-01")

        assert len(results) == 3


class TestFetchDocSubcommand:
    """Test fetch doc subcommand."""

    def test_fetch_doc_single_url(self):
        """Test fetching single document."""
        fetcher = MockFetcher()
        cmd = FetchDocSubcommand(fetcher)
        results = cmd.run(["https://example.com/page1"])

        assert len(results) == 1
        assert "Content from" in results[0].content_text

    def test_fetch_doc_multiple_urls(self):
        """Test fetching multiple documents."""
        fetcher = MockFetcher()
        cmd = FetchDocSubcommand(fetcher)
        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
        results = cmd.run(urls)

        assert len(results) == 3
        assert all(r.word_count > 0 for r in results)

    def test_fetch_doc_with_engine(self):
        """Test fetching with specific engine."""
        fetcher = MockFetcher()
        cmd = FetchDocSubcommand(fetcher)
        results = cmd.run(["https://example.com"], engine="trafilatura")

        assert len(results) == 1


class TestFetchProfileSubcommand:
    """Test fetch profile subcommand."""

    def test_fetch_profile_single(self):
        """Test fetching single profile."""
        fetcher = MockFetcher()
        cmd = FetchProfileSubcommand(fetcher)
        results = cmd.run(["https://twitter.com/user"], platform="twitter")

        assert len(results) == 1
        assert results[0].platform == "twitter"

    def test_fetch_profile_multiple(self):
        """Test fetching multiple profiles."""
        fetcher = MockFetcher()
        cmd = FetchProfileSubcommand(fetcher)
        urls = [
            "https://linkedin.com/in/john",
            "https://linkedin.com/in/jane",
        ]
        results = cmd.run(urls, platform="linkedin")

        assert len(results) == 2
        assert all(r.platform == "linkedin" for r in results)

    def test_fetch_profile_content(self):
        """Test fetched profile has content."""
        fetcher = MockFetcher()
        cmd = FetchProfileSubcommand(fetcher)
        results = cmd.run(["https://twitter.com/user"], platform="twitter")

        assert results[0].bio is not None


class TestFetchPostsSubcommand:
    """Test fetch posts subcommand."""

    def test_fetch_posts_single(self):
        """Test fetching single post."""
        fetcher = MockFetcher()
        cmd = FetchPostsSubcommand(fetcher)
        results = cmd.run(["https://twitter.com/user/status/123"], platform="twitter")

        assert len(results) == 1
        assert results[0].platform == "twitter"

    def test_fetch_posts_multiple(self):
        """Test fetching multiple posts."""
        fetcher = MockFetcher()
        cmd = FetchPostsSubcommand(fetcher)
        urls = [
            "https://twitter.com/user/status/1",
            "https://twitter.com/user/status/2",
        ]
        results = cmd.run(urls, platform="twitter")

        assert len(results) == 2
        assert all(r.published_at is not None for r in results)

    def test_fetch_posts_different_platforms(self):
        """Test fetching posts from different platforms."""
        fetcher = MockFetcher()

        for platform in ["twitter", "linkedin"]:
            cmd = FetchPostsSubcommand(fetcher)
            results = cmd.run([f"https://{platform}.com/post"], platform=platform)

            assert all(r.platform == platform for r in results)


class TestSubcommandIntegration:
    """Test subcommand integration."""

    def test_map_then_fetch_flow(self):
        """Test typical map then fetch flow."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        # Map phase
        map_cmd = MapDocSubcommand(mapper)
        doc_metas = map_cmd.run("https://example.com")

        # Fetch phase
        fetch_cmd = FetchDocSubcommand(fetcher)
        docs = fetch_cmd.run([m.url for m in doc_metas])

        assert len(docs) == len(doc_metas)
        assert all(d.content_text for d in docs)

    def test_map_profile_then_fetch(self):
        """Test map profiles then fetch flow."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        # Map phase
        map_cmd = MapProfileSubcommand(mapper)
        profiles_meta = map_cmd.run("AI engineer", platform="linkedin")

        # Fetch phase
        fetch_cmd = FetchProfileSubcommand(fetcher)
        profiles = fetch_cmd.run([m.url for m in profiles_meta], platform="linkedin")

        assert len(profiles) == len(profiles_meta)
        assert all(p.platform == "linkedin" for p in profiles)

    def test_map_posts_then_fetch(self):
        """Test map posts then fetch flow."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        # Map phase
        map_cmd = MapPostsSubcommand(mapper)
        posts_meta = map_cmd.run("ai", limit=100)

        # Fetch phase
        fetch_cmd = FetchPostsSubcommand(fetcher)
        posts = fetch_cmd.run([p.url for p in posts_meta], platform="twitter")

        assert len(posts) == len(posts_meta)
        assert all(p.content_text for p in posts)
