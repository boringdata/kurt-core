"""Map subcommands for content discovery."""

from typing import Optional

from kurt.tools.map.core import BaseMapper, MapperConfig
from kurt.tools.map.core.models import DocMetadata, PostMetadata, ProfileMetadata
from kurt.tools.map.models import DocType


class MapDocSubcommand:
    """Map doc subcommand - discover document URLs."""

    def __init__(self, mapper: BaseMapper):
        """Initialize mapper."""
        self.mapper = mapper

    def run(
        self,
        url: str,
        depth: int = 3,
        include_pattern: Optional[str] = None,
        exclude_pattern: Optional[str] = None,
    ) -> list[DocMetadata]:
        """Map documents from a URL.

        Args:
            url: Base URL to map
            depth: Crawl depth limit
            include_pattern: URL inclusion pattern
            exclude_pattern: URL exclusion pattern

        Returns:
            List of discovered DocMetadata
        """
        config = MapperConfig(
            max_depth=depth,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
        )
        self.mapper.config = config

        result = self.mapper.map(url, DocType.DOC)

        return [
            DocMetadata(url=doc_url, discovered_from=url, depth=0)
            for doc_url in result.urls
        ]


class MapProfileSubcommand:
    """Map profile subcommand - discover social media profiles."""

    def __init__(self, mapper: BaseMapper):
        """Initialize mapper."""
        self.mapper = mapper

    def run(
        self,
        query: str,
        platform: str,
        limit: int = 100,
    ) -> list[ProfileMetadata]:
        """Map profiles matching query.

        Args:
            query: Search query
            platform: Platform to search (twitter, linkedin, etc.)
            limit: Max results

        Returns:
            List of discovered ProfileMetadata
        """
        config = MapperConfig(max_urls=limit, platform=platform)
        self.mapper.config = config

        result = self.mapper.map(query, DocType.PROFILE)

        return [
            ProfileMetadata(
                platform=platform,
                username=f"user_{i}",
                url=url,
            )
            for i, url in enumerate(result.urls[:limit])
        ]


class MapPostsSubcommand:
    """Map posts subcommand - discover social media posts."""

    def __init__(self, mapper: BaseMapper):
        """Initialize mapper."""
        self.mapper = mapper

    def run(
        self,
        source: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> list[PostMetadata]:
        """Map posts from profiles or source.

        Args:
            source: Profile URL or query
            limit: Max results
            since: Date filter (YYYY-MM-DD)

        Returns:
            List of discovered PostMetadata
        """
        from datetime import datetime

        config = MapperConfig(max_urls=limit)
        self.mapper.config = config

        result = self.mapper.map(source or "", DocType.POSTS)

        posts = []
        for i, url in enumerate(result.urls[:limit]):
            posts.append(
                PostMetadata(
                    platform="unknown",
                    post_id=f"post_{i}",
                    url=url,
                    published_at=datetime.now(),
                )
            )

        return posts
