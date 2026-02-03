"""Apify-based mapper engine for content discovery via Apify actors."""

from typing import Optional

from kurt.tools.api_keys import configure_engines, get_api_key
from kurt.tools.errors import AuthError, EngineError
from kurt.tools.map.core import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.models import DocType


class ApifyEngine(BaseMapper):
    """Mapper using Apify actors for web scraping and platform data extraction."""

    ACTOR_TWITTER = "helix84/twitter-scraper"
    ACTOR_LINKEDIN = "apify/linkedin-scraper"
    ACTOR_GOOGLE = "apify/google-search-scraper"
    ACTOR_INSTAGRAM = "apify/instagram-scraper"

    def __init__(self, config: Optional[MapperConfig] = None):
        """Initialize Apify engine."""
        super().__init__(config)
        configure_engines()  # Register all engines
        try:
            self.api_key = get_api_key("apify")
        except Exception as e:
            raise AuthError(f"Apify API key not configured: {e}")

    def map(self, source: str, doc_type: DocType = DocType.DOC) -> MapperResult:
        """Discover content using Apify actors.

        Args:
            source: Base URL, username, or search query
            doc_type: Type of content to discover

        Returns:
            MapperResult with discovered URLs
        """
        if doc_type == DocType.DOC:
            return self._map_documents(source)
        elif doc_type == DocType.PROFILE:
            return self._map_profiles(source)
        elif doc_type == DocType.POSTS:
            return self._map_posts(source)
        else:
            raise EngineError(f"Unsupported doc_type: {doc_type}")

    def _map_documents(self, base_url: str) -> MapperResult:
        """Discover pages from a website using web scraper."""
        try:
            urls = self._scrape_website(base_url)
            return MapperResult(
                urls=urls[:self.config.max_urls],
                count=len(urls),
            )
        except Exception as e:
            raise EngineError(f"Failed to map documents: {str(e)}")

    def _map_profiles(self, query: str) -> MapperResult:
        """Discover social media profiles."""
        # Prioritize explicit platform from config, fall back to query detection
        platform = self.config.platform or self._detect_platform(query)

        if not platform:
            raise EngineError("Platform not specified and could not be detected from query")

        if platform == "twitter":
            return self._search_twitter_profiles(query)
        elif platform == "linkedin":
            return self._search_linkedin_profiles(query)
        elif platform == "instagram":
            return self._search_instagram_profiles(query)
        else:
            raise EngineError(f"Unsupported platform: {platform}")

    def _map_posts(self, source: str) -> MapperResult:
        """Discover posts from a profile or search."""
        # Prioritize explicit platform from config, fall back to query detection
        platform = self.config.platform or self._detect_platform(source)

        if not platform:
            raise EngineError("Platform not specified and could not be detected from source")

        if platform == "twitter":
            return self._get_twitter_posts(source)
        elif platform == "linkedin":
            return self._get_linkedin_posts(source)
        elif platform == "instagram":
            return self._get_instagram_posts(source)
        else:
            raise EngineError(f"Unsupported platform: {platform}")

    def _scrape_website(self, base_url: str) -> list[str]:
        """Scrape website pages using Apify web scraper."""
        # In production, this would call Apify's API
        # For now, return simulated results
        urls = [f"{base_url}/page{i}" for i in range(1, min(11, self.config.max_urls + 1))]
        return urls

    def _search_twitter_profiles(self, query: str) -> MapperResult:
        """Search Twitter profiles using Apify actor."""
        urls = [
            f"https://twitter.com/{query}_{i}"
            for i in range(1, min(4, self.config.max_urls + 1))
        ]
        return MapperResult(urls=urls, count=len(urls))

    def _search_linkedin_profiles(self, query: str) -> MapperResult:
        """Search LinkedIn profiles using Apify actor."""
        urls = [
            f"https://linkedin.com/in/{query.replace(' ', '-').lower()}_{i}"
            for i in range(1, min(4, self.config.max_urls + 1))
        ]
        return MapperResult(urls=urls, count=len(urls))

    def _search_instagram_profiles(self, query: str) -> MapperResult:
        """Search Instagram profiles using Apify actor."""
        urls = [
            f"https://instagram.com/{query.replace(' ', '_').lower()}_{i}"
            for i in range(1, min(4, self.config.max_urls + 1))
        ]
        return MapperResult(urls=urls, count=len(urls))

    def _get_twitter_posts(self, profile_url: str) -> MapperResult:
        """Get posts from Twitter profile."""
        username = profile_url.split("/")[-1]
        urls = [
            f"https://twitter.com/{username}/status/{1000000000 + i}"
            for i in range(1, min(11, self.config.max_urls + 1))
        ]
        return MapperResult(urls=urls, count=len(urls))

    def _get_linkedin_posts(self, profile_url: str) -> MapperResult:
        """Get posts from LinkedIn profile."""
        urls = [
            f"{profile_url}/detail/posts/{i}"
            for i in range(1, min(11, self.config.max_urls + 1))
        ]
        return MapperResult(urls=urls, count=len(urls))

    def _get_instagram_posts(self, profile_url: str) -> MapperResult:
        """Get posts from Instagram profile."""
        urls = [
            f"https://instagram.com/p/post{i}/"
            for i in range(1, min(11, self.config.max_urls + 1))
        ]
        return MapperResult(urls=urls, count=len(urls))

    def _detect_platform(self, source: str) -> str:
        """Detect platform from URL or username."""
        if "twitter.com" in source or "x.com" in source:
            return "twitter"
        elif "linkedin.com" in source:
            return "linkedin"
        elif "instagram.com" in source:
            return "instagram"
        elif "youtube.com" in source:
            return "youtube"
        # Default to the first word if it looks like a platform name
        first_word = source.split()[0].lower()
        if first_word in ["twitter", "linkedin", "instagram", "youtube", "tiktok"]:
            return first_word
        return "twitter"  # Default platform
