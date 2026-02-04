"""Integration and E2E tests for map/fetch workflows."""


import pytest

from kurt.tools.fetch.core import BaseFetcher, FetchResult
from kurt.tools.fetch.subcommands import (
    FetchDocSubcommand,
    FetchPostsSubcommand,
    FetchProfileSubcommand,
)
from kurt.tools.map.core import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.models import DocType
from kurt.tools.map.subcommands import (
    MapDocSubcommand,
    MapPostsSubcommand,
    MapProfileSubcommand,
)


class MockMapper(BaseMapper):
    """Mock mapper for testing."""

    def map(self, source: str, doc_type: DocType = DocType.DOC) -> MapperResult:
        """Mock map implementation."""
        base_urls = {
            DocType.DOC: [f"{source}/page{i}" for i in range(1, 6)],
            DocType.PROFILE: [f"https://twitter.com/user{i}" for i in range(1, 4)],
            DocType.POSTS: [f"https://twitter.com/user/status/{1000000 + i}" for i in range(1, 6)],
        }
        urls = base_urls.get(doc_type, [])
        return MapperResult(urls=urls[:self.config.max_urls], count=len(urls))


class MockFetcher(BaseFetcher):
    """Mock fetcher for testing."""

    def fetch(self, url: str) -> FetchResult:
        """Mock fetch implementation."""
        return FetchResult(
            content=f"Content from {url}",
            content_html=f"<p>Content from {url}</p>",
            metadata={"url": url},
            success=True,
        )


class TestMapFetchIntegration:
    """Test integration between map and fetch operations."""

    def test_map_doc_then_fetch_basic(self):
        """Test mapping documents then fetching their content."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        # Map phase
        map_cmd = MapDocSubcommand(mapper)
        doc_metas = map_cmd.run("https://example.com", depth=2)

        assert len(doc_metas) > 0
        assert all(m.url.startswith("https://") for m in doc_metas)

        # Fetch phase
        fetch_cmd = FetchDocSubcommand(fetcher)
        docs = fetch_cmd.run([m.url for m in doc_metas])

        assert len(docs) == len(doc_metas)
        assert all(d.content_text for d in docs)

    def test_map_profiles_then_fetch_twitter(self):
        """Test mapping Twitter profiles then fetching details."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        # Map phase
        map_cmd = MapProfileSubcommand(mapper)
        profiles_meta = map_cmd.run("AI engineer", platform="twitter", limit=50)

        assert len(profiles_meta) > 0
        assert all(p.platform == "twitter" for p in profiles_meta)

        # Fetch phase
        fetch_cmd = FetchProfileSubcommand(fetcher)
        profiles = fetch_cmd.run([p.url for p in profiles_meta], platform="twitter")

        assert len(profiles) == len(profiles_meta)
        assert all(p.platform == "twitter" for p in profiles)
        assert all(p.bio is not None for p in profiles)

    def test_map_profiles_then_fetch_linkedin(self):
        """Test mapping LinkedIn profiles then fetching details."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        # Map phase
        map_cmd = MapProfileSubcommand(mapper)
        profiles_meta = map_cmd.run("data scientist", platform="linkedin", limit=25)

        assert len(profiles_meta) > 0

        # Fetch phase
        fetch_cmd = FetchProfileSubcommand(fetcher)
        profiles = fetch_cmd.run([p.url for p in profiles_meta], platform="linkedin")

        assert len(profiles) == len(profiles_meta)

    def test_map_posts_then_fetch_full_content(self):
        """Test mapping posts then fetching full content."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        # Map phase
        map_cmd = MapPostsSubcommand(mapper)
        posts_meta = map_cmd.run("AI", limit=50)

        assert len(posts_meta) > 0

        # Fetch phase
        fetch_cmd = FetchPostsSubcommand(fetcher)
        posts = fetch_cmd.run([p.url for p in posts_meta], platform="twitter")

        assert len(posts) == len(posts_meta)
        assert all(p.published_at is not None for p in posts)
        assert all(p.content_text for p in posts)

    def test_multi_platform_profile_discovery_and_fetch(self):
        """Test discovering and fetching profiles from multiple platforms."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        platforms = ["twitter", "linkedin", "instagram"]
        all_profiles = []

        for platform in platforms:
            map_cmd = MapProfileSubcommand(mapper)
            profiles_meta = map_cmd.run("developer", platform=platform, limit=20)

            fetch_cmd = FetchProfileSubcommand(fetcher)
            profiles = fetch_cmd.run([p.url for p in profiles_meta], platform=platform)

            assert all(p.platform == platform for p in profiles)
            all_profiles.extend(profiles)

        assert len(all_profiles) >= len(platforms)

    def test_end_to_end_document_mapping_and_content_extraction(self):
        """End-to-end test of document mapping and content extraction."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        base_url = "https://example.com"

        # Stage 1: Discover documents
        map_cmd = MapDocSubcommand(mapper)
        discovered = map_cmd.run(
            base_url,
            depth=3,
            include_pattern=r".*blog.*",
            exclude_pattern=r".*admin.*",
        )

        assert len(discovered) > 0
        assert all(d.discovered_from == base_url for d in discovered)

        # Stage 2: Filter and prepare for fetching
        urls_to_fetch = [d.url for d in discovered]
        assert len(urls_to_fetch) <= 5  # Limited by mock

        # Stage 3: Fetch content
        fetch_cmd = FetchDocSubcommand(fetcher)
        content = fetch_cmd.run(urls_to_fetch, engine="trafilatura")

        assert len(content) == len(urls_to_fetch)
        assert all(c.word_count >= 0 for c in content)

        # Stage 4: Verify correlation
        for meta, doc in zip(discovered, content):
            assert meta.url == doc.url

    def test_error_handling_in_integrated_workflow(self):
        """Test error handling across map and fetch stages."""
        class FailingMapper(BaseMapper):
            def map(self, source: str, doc_type: DocType = DocType.DOC) -> MapperResult:
                raise Exception("Mapper failed")

        class FailingFetcher(BaseFetcher):
            def fetch(self, url: str) -> FetchResult:
                raise Exception("Fetcher failed")

        failing_mapper = FailingMapper()
        failing_fetcher = FailingFetcher()

        # Test map failure
        map_cmd = MapDocSubcommand(failing_mapper)
        with pytest.raises(Exception):
            map_cmd.run("https://example.com")

        # Test fetch failure
        fetch_cmd = FetchDocSubcommand(failing_fetcher)
        with pytest.raises(Exception):
            fetch_cmd.run(["https://example.com/page1"])

    def test_large_batch_processing(self):
        """Test processing large batches of URLs."""
        mapper = MockMapper(MapperConfig(max_urls=100))
        fetcher = MockFetcher()

        # Map phase with large limit
        map_cmd = MapDocSubcommand(mapper)
        docs = map_cmd.run("https://example.com")

        # Fetch phase with batch
        fetch_cmd = FetchDocSubcommand(fetcher)
        results = fetch_cmd.run([d.url for d in docs])

        assert len(results) == len(docs)

    def test_concurrent_platform_operations(self):
        """Test concurrent operations on multiple platforms."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        # Simulate concurrent platform discovery
        platforms = ["twitter", "linkedin", "instagram"]
        all_results = {}

        for platform in platforms:
            # Map
            map_cmd = MapProfileSubcommand(mapper)
            profiles = map_cmd.run("test query", platform=platform)

            # Fetch
            fetch_cmd = FetchProfileSubcommand(fetcher)
            content = fetch_cmd.run([p.url for p in profiles], platform=platform)

            all_results[platform] = {
                "discovered": len(profiles),
                "fetched": len(content),
            }

        # Verify all platforms processed
        assert len(all_results) == 3
        for platform in platforms:
            assert all_results[platform]["discovered"] > 0
            assert all_results[platform]["fetched"] > 0

    def test_data_consistency_across_stages(self):
        """Test data consistency throughout the pipeline."""
        mapper = MockMapper()
        fetcher = MockFetcher()

        base_url = "https://example.com"

        # Map
        map_cmd = MapDocSubcommand(mapper)
        discovered = map_cmd.run(base_url)

        # Fetch
        fetch_cmd = FetchDocSubcommand(fetcher)
        fetched = fetch_cmd.run([d.url for d in discovered])

        # Verify consistency
        for d, f in zip(discovered, fetched):
            assert d.url == f.url
            assert len(f.content_text) > 0

        # Verify no loss of data
        assert len(discovered) == len(fetched)
