"""Fetch subcommands for content retrieval."""

from datetime import datetime
from typing import Optional

from kurt.tools.fetch.core import BaseFetcher
from kurt.tools.map.core.models import DocContent, PostContent, ProfileContent


class FetchDocSubcommand:
    """Fetch doc subcommand - retrieve document content."""

    def __init__(self, fetcher: BaseFetcher):
        """Initialize fetcher."""
        self.fetcher = fetcher

    def run(
        self,
        urls: list[str],
        engine: Optional[str] = None,
    ) -> list[DocContent]:
        """Fetch document content.

        Args:
            urls: URLs to fetch
            engine: Fetcher engine to use

        Returns:
            List of DocContent
        """
        contents = []
        for url in urls:
            result = self.fetcher.fetch(url)
            contents.append(
                DocContent(
                    url=url,
                    content_text=result.content,
                    content_html=result.content_html,
                    word_count=len(result.content.split()),
                )
            )
        return contents


class FetchProfileSubcommand:
    """Fetch profile subcommand - retrieve full profile details."""

    def __init__(self, fetcher: BaseFetcher):
        """Initialize fetcher."""
        self.fetcher = fetcher

    def run(
        self,
        profile_urls: list[str],
        platform: str,
    ) -> list[ProfileContent]:
        """Fetch profile content.

        Args:
            profile_urls: Profile URLs to fetch
            platform: Platform (twitter, linkedin, etc.)

        Returns:
            List of ProfileContent
        """
        profiles = []
        for url in profile_urls:
            result = self.fetcher.fetch(url)
            profiles.append(
                ProfileContent(
                    url=url,
                    platform=platform,
                    username=url.split("/")[-1],
                    bio=result.content[:500] if result.content else None,
                )
            )
        return profiles


class FetchPostsSubcommand:
    """Fetch posts subcommand - retrieve full post content."""

    def __init__(self, fetcher: BaseFetcher):
        """Initialize fetcher."""
        self.fetcher = fetcher

    def run(
        self,
        post_urls: list[str],
        platform: str,
    ) -> list[PostContent]:
        """Fetch post content.

        Args:
            post_urls: Post URLs to fetch
            platform: Platform (twitter, linkedin, etc.)

        Returns:
            List of PostContent
        """
        posts = []
        for url in post_urls:
            result = self.fetcher.fetch(url)
            posts.append(
                PostContent(
                    url=url,
                    platform=platform,
                    post_id=url.split("/")[-1],
                    content_text=result.content,
                    published_at=datetime.now(),
                )
            )
        return posts
