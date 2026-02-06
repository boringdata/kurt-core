"""Apify-based content mapping engine for social platforms.

Uses the ApifyClient from kurt.integrations.apify to discover content
from Twitter, LinkedIn, Threads, and Substack.
"""

from __future__ import annotations

from typing import Optional

from kurt.integrations.apify import (
    ApifyAuthError,
    ApifyClient,
    ApifyError,
    ApifyTimeoutError,
    get_default_actor,
    get_profile_actor,
    list_actors,
    list_platforms,
)
from kurt.tools.errors import AuthError, EngineError
from kurt.tools.errors import TimeoutError as EngineTimeoutError
from kurt.tools.map.core import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.models import DocType


class ApifyMapperConfig(MapperConfig):
    """Configuration for Apify mapper.

    Attributes:
        api_key: Apify API token (uses APIFY_API_KEY env var if not provided)
        platform: Platform name (twitter, linkedin, threads, substack)
        apify_actor: Specific actor ID to use (overrides platform default)
        max_items: Maximum items to return from Apify
    """

    api_key: Optional[str] = None
    platform: Optional[str] = None
    apify_actor: Optional[str] = None
    max_items: int = 50


class ApifyEngine(BaseMapper):
    """Maps content using Apify actors for social platform content discovery.

    Supports:
    - Twitter/X: Search tweets, discover profiles
    - LinkedIn: Search posts, discover profiles
    - Threads: Search posts
    - Substack: Discover newsletter posts

    Usage:
        # Easy mode: use platform shortcut
        config = ApifyMapperConfig(platform="twitter")
        engine = ApifyEngine(config)
        result = engine.map("AI agents", DocType.POSTS)

        # Power user mode: specific actor
        config = ApifyMapperConfig(apify_actor="apidojo/tweet-scraper")
        engine = ApifyEngine(config)
        result = engine.map("machine learning", DocType.POSTS)
    """

    def __init__(self, config: Optional[MapperConfig] = None):
        """Initialize Apify engine.

        Args:
            config: Mapper configuration (ApifyMapperConfig for full control)

        Raises:
            AuthError: If Apify API key not configured
        """
        # Convert base MapperConfig to ApifyMapperConfig if needed
        if config is None:
            config = ApifyMapperConfig()
        elif not isinstance(config, ApifyMapperConfig):
            config = ApifyMapperConfig(**config.model_dump())

        super().__init__(config)
        self._config: ApifyMapperConfig = self.config  # type: ignore

        try:
            self._client = ApifyClient(api_key=self._config.api_key)
        except ApifyAuthError:
            raise AuthError(
                "APIFY_API_KEY environment variable is not set. "
                "Get your API key from https://console.apify.com/account/integrations"
            )

    def map(
        self,
        source: str,
        doc_type: DocType = DocType.POSTS,
    ) -> MapperResult:
        """Discover content using Apify actors.

        Args:
            source: Query string, URL, or username to search
            doc_type: Type of content to discover:
                - DocType.PROFILE: Discover profile information
                - DocType.POSTS: Discover posts/content
                - DocType.DOC: Generic document discovery

        Returns:
            MapperResult with discovered URLs and metadata

        Raises:
            EngineError: If platform not specified and can't be detected
        """
        try:
            # Determine platform
            platform = self._config.platform or self._detect_platform(source)
            if not platform and not self._config.apify_actor:
                raise EngineError(
                    "Platform not specified and could not be detected from source. "
                    "Use --platform or --apify-actor option."
                )

            # Get actor to use
            actor_id = self._get_actor(platform, doc_type)

            # Run the actor
            items = self._client.fetch(
                query=source,
                actor_id=actor_id,
                platform=platform if not actor_id else None,
                max_items=self._config.max_items,
            )

            # Extract URLs from results
            urls = []
            for item in items:
                if item.url:
                    urls.append(item.url)
                elif item.id:
                    # Construct URL from ID if possible
                    url = self._construct_url(item.id, platform)
                    if url:
                        urls.append(url)

            # Limit to max_urls from config
            urls = urls[: self._config.max_urls]

            return MapperResult(
                urls=urls,
                count=len(urls),
                metadata={
                    "engine": "apify",
                    "platform": platform,
                    "actor": actor_id,
                    "doc_type": doc_type.value,
                    "query": source,
                    "total_items": len(items),
                },
            )

        except ApifyTimeoutError as e:
            raise EngineTimeoutError(str(e))
        except ApifyAuthError as e:
            raise AuthError(str(e))
        except ApifyError as e:
            raise EngineError(f"Apify error: {e}")

    def _get_actor(self, platform: Optional[str], doc_type: DocType) -> Optional[str]:
        """Determine which actor to use based on config and doc_type.

        Args:
            platform: Platform name
            doc_type: Type of content

        Returns:
            Actor ID to use, or None to use platform default
        """
        # Explicit actor from config takes precedence
        if self._config.apify_actor:
            return self._config.apify_actor

        if not platform:
            return None

        # Use profile-specific actor for PROFILE doc type
        if doc_type == DocType.PROFILE:
            return get_profile_actor(platform)

        # Use default actor for platform
        return get_default_actor(platform)

    def _detect_platform(self, source: str) -> Optional[str]:
        """Detect platform from URL or query.

        Args:
            source: URL, username, or query string

        Returns:
            Platform name or None if can't be detected
        """
        source_lower = source.lower()

        # Check URL patterns
        if "twitter.com" in source_lower or "x.com" in source_lower:
            return "twitter"
        elif "linkedin.com" in source_lower:
            return "linkedin"
        elif "threads.net" in source_lower:
            return "threads"
        elif "substack.com" in source_lower or ".substack.com" in source_lower:
            return "substack"

        # Check for @ prefix (likely Twitter/X handle)
        if source.startswith("@"):
            return "twitter"

        return None

    def _construct_url(self, item_id: str, platform: Optional[str]) -> Optional[str]:
        """Construct URL from item ID.

        Args:
            item_id: Item identifier
            platform: Platform name

        Returns:
            Constructed URL or None
        """
        if not platform:
            return None

        platform_lower = platform.lower()

        if platform_lower == "twitter":
            # If it looks like a username, make profile URL
            if not item_id.isdigit():
                return f"https://twitter.com/{item_id}"
            # Otherwise it's a tweet ID
            return f"https://twitter.com/i/status/{item_id}"
        elif platform_lower == "linkedin":
            return f"https://linkedin.com/posts/{item_id}"
        elif platform_lower == "substack":
            return f"https://substack.com/p/{item_id}"

        return None

    @staticmethod
    def list_actors() -> list[dict[str, str]]:
        """List all available Apify actors.

        Returns:
            List of actor info dicts with actor_id, source_name, description
        """
        return list_actors()

    @staticmethod
    def list_platforms() -> list[str]:
        """List supported platforms.

        Returns:
            List of platform names
        """
        return list_platforms()
