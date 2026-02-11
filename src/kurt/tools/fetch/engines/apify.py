"""Apify-based content fetching engine for social platforms.

Uses the ApifyClient from kurt.integrations.apify to extract content
from Twitter, LinkedIn, Threads, and Substack.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from kurt.integrations.apify import (
    ApifyAuthError,
    ApifyClient,
    ApifyError,
    ApifyTimeoutError,
    get_default_actor,
    get_profile_actor,
)
from kurt.tools.errors import AuthError, EngineError
from kurt.tools.errors import TimeoutError as EngineTimeoutError
from kurt.tools.fetch.core import BaseFetcher, FetcherConfig, FetchResult


class ApifyFetcherConfig(FetcherConfig):
    """Configuration for Apify fetcher.

    Attributes:
        api_key: Apify API token (uses APIFY_API_KEY env var if not provided)
        platform: Platform name (twitter, linkedin, threads, substack)
        apify_actor: Specific actor ID to use (overrides platform default)
        content_type: Content type override (auto, doc, profile, post)
        max_items: Maximum items to fetch (for profile posts)
    """

    api_key: Optional[str] = None
    platform: Optional[str] = None
    apify_actor: Optional[str] = None
    content_type: Optional[str] = None  # auto, doc, profile, post
    max_items: int = 20


class ApifyFetcher(BaseFetcher):
    """Fetches content using Apify actors from social platforms.

    Supports:
    - Twitter/X: Fetch tweets and profile content
    - LinkedIn: Fetch posts and profile content
    - Threads: Fetch posts
    - Substack: Fetch newsletter posts

    Usage:
        config = ApifyFetcherConfig()
        fetcher = ApifyFetcher(config)
        result = fetcher.fetch("https://twitter.com/username")
    """

    name = "apify"
    version = "1.0.0"
    url_patterns = [
        # Twitter/X handled by dedicated twitterapi provider
        "*linkedin.com/*",
        "*threads.net/*",
        "*substack.com/*",
    ]
    requires_env = ["APIFY_API_KEY"]

    from kurt.tools.fetch.providers.apify.config import ApifyFetchProviderConfig
    ConfigModel = ApifyFetchProviderConfig

    def __init__(self, config: Optional[FetcherConfig] = None):
        """Initialize Apify fetcher.

        Args:
            config: Fetcher configuration (ApifyFetcherConfig for full control)

        Raises:
            AuthError: If Apify API key not configured
        """
        # Convert base FetcherConfig to ApifyFetcherConfig if needed
        if config is None:
            config = ApifyFetcherConfig()
        elif not isinstance(config, ApifyFetcherConfig):
            config = ApifyFetcherConfig(**config.model_dump())

        super().__init__(config)
        self._config: ApifyFetcherConfig = self.config  # type: ignore

        try:
            self._client = ApifyClient(api_key=self._config.api_key)
        except ApifyAuthError:
            raise AuthError(
                "APIFY_API_KEY environment variable is not set. "
                "Get your API key from https://console.apify.com/account/integrations"
            )

    def fetch(self, url: str) -> FetchResult:
        """Fetch content from URL using appropriate Apify actor.

        Args:
            url: URL to fetch (social media profile, post, or newsletter)

        Returns:
            FetchResult with extracted content in markdown format

        Raises:
            EngineError: If platform not supported or fetch fails
        """
        try:
            # Detect platform from URL
            platform = self._config.platform or self._detect_platform(url)

            if not platform and not self._config.apify_actor:
                raise EngineError(
                    f"Could not detect platform from URL: {url}. "
                    "Use --platform or --apify-actor option."
                )

            # Determine if this is a profile or post URL
            # Use explicit content_type if provided, otherwise auto-detect
            content_type = self._config.content_type
            if content_type and content_type != "auto":
                is_profile = content_type == "profile"
            else:
                is_profile = self._is_profile_url(url, platform)

            # Get actor to use
            actor_id = self._get_actor(platform, is_profile)

            # Run the actor
            items = self._client.fetch(
                query=url,
                actor_id=actor_id,
                platform=platform if not actor_id else None,
                max_items=self._config.max_items,
            )

            if not items:
                return FetchResult(
                    content="",
                    metadata={
                        "engine": "apify",
                        "platform": platform,
                        "actor": actor_id,
                        "url": url,
                        "empty": True,
                        "fetched_at": datetime.now().isoformat(),
                    },
                    success=False,
                )

            # Format content as markdown
            content = self._format_content(items, platform, url)

            return FetchResult(
                content=content,
                metadata={
                    "engine": "apify",
                    "platform": platform,
                    "actor": actor_id,
                    "url": url,
                    "item_count": len(items),
                    "fetched_at": datetime.now().isoformat(),
                },
                success=True,
            )

        except ApifyTimeoutError as e:
            raise EngineTimeoutError(str(e))
        except ApifyAuthError as e:
            raise AuthError(str(e))
        except ApifyError as e:
            raise EngineError(f"Apify error: {e}")

    def _get_actor(self, platform: Optional[str], is_profile: bool) -> Optional[str]:
        """Determine which actor to use.

        Args:
            platform: Platform name
            is_profile: Whether URL is a profile URL

        Returns:
            Actor ID or None to use platform default
        """
        # Explicit actor from config takes precedence
        if self._config.apify_actor:
            return self._config.apify_actor

        if not platform:
            return None

        # Use profile-specific actor if fetching profile
        if is_profile:
            return get_profile_actor(platform)

        return get_default_actor(platform)

    def _detect_platform(self, url: str) -> Optional[str]:
        """Detect platform from URL.

        Args:
            url: URL to check

        Returns:
            Platform name or None
        """
        url_lower = url.lower()

        if "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        elif "linkedin.com" in url_lower:
            return "linkedin"
        elif "threads.net" in url_lower:
            return "threads"
        elif "substack.com" in url_lower or ".substack.com" in url_lower:
            return "substack"

        return None

    def _is_profile_url(self, url: str, platform: Optional[str]) -> bool:
        """Check if URL is a profile URL vs a post URL.

        Args:
            url: URL to check
            platform: Platform name

        Returns:
            True if profile URL, False if post URL
        """
        if not platform:
            return False

        url_lower = url.lower()
        platform_lower = platform.lower()

        if platform_lower == "twitter":
            # Profile: twitter.com/username
            # Post: twitter.com/username/status/12345
            return "/status/" not in url_lower
        elif platform_lower == "linkedin":
            # Profile: linkedin.com/in/username
            # Post: linkedin.com/posts/... or linkedin.com/feed/update/...
            return "/in/" in url_lower and "/posts/" not in url_lower
        elif platform_lower == "substack":
            # Profile: newsletter.substack.com
            # Post: newsletter.substack.com/p/post-slug
            return "/p/" not in url_lower

        return True  # Default to profile for unknown platforms

    def _format_content(
        self, items: list, platform: Optional[str], url: str
    ) -> str:
        """Format fetched items as markdown content.

        Args:
            items: List of ParsedItem objects
            platform: Platform name
            url: Original URL

        Returns:
            Formatted markdown content
        """
        if not items:
            return ""

        # Use the first item as the main content
        item = items[0]
        lines = []

        # Add title if available
        if item.title:
            lines.append(f"# {item.title}")
            lines.append("")

        # Add author/source info
        if item.author:
            lines.append(f"**Author:** {item.author}")
        if item.timestamp:
            lines.append(f"**Date:** {item.timestamp}")
        if item.url:
            lines.append(f"**URL:** {item.url}")

        if lines:
            lines.append("")

        # Add main content
        if item.text:
            lines.append(item.text)
            lines.append("")

        # For profiles with multiple items (e.g., recent posts), add them
        if len(items) > 1:
            lines.append("## Recent Content")
            lines.append("")
            for i, post in enumerate(items[1:10], 1):  # Limit to 10 additional items
                if post.title:
                    lines.append(f"### {i}. {post.title}")
                elif post.text:
                    preview = post.text[:100] + "..." if len(post.text) > 100 else post.text
                    lines.append(f"### {i}. {preview}")

                if post.text and len(post.text) > 100:
                    lines.append(post.text)
                if post.url:
                    lines.append(f"[Read more]({post.url})")
                lines.append("")

        return "\n".join(lines)


# Alias for backward compatibility
ApifyEngine = ApifyFetcher
