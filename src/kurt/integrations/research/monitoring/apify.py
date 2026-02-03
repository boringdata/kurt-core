"""
Apify adapter for social media monitoring.

Uses the shared Apify integration layer for Twitter/X, LinkedIn, Threads, and Substack.
Requires an API token configured in kurt.config as RESEARCH_APIFY_API_TOKEN.

This adapter wraps the shared ApifyClient to provide Signal objects for
backward compatibility with the SignalsTool and research monitoring system.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Callable, Optional

from kurt.integrations.apify.client import ApifyClient, ApifyAuthError, ApifyError
from kurt.integrations.apify.registry import (
    ACTOR_REGISTRY,
    PLATFORM_DEFAULTS,
    PROFILE_ACTORS,
    ActorConfig,
    get_actor_config,
    get_default_actor,
    get_profile_actor,
    guess_source_from_actor,
    list_actors as _list_actors,
)
from kurt.integrations.apify.parsers import (
    FieldMapping,
    ParsedItem,
    parse_items,
)
from kurt.integrations.research.monitoring.models import Signal


def _build_generic_search_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build generic search input - works for many actors."""
    return {
        "searchTerms": [query],
        "maxItems": max_items,
        **kwargs,
    }


# Re-export for backward compatibility
__all__ = [
    "ApifyAdapter",
    "FieldMapping",
    "ActorConfig",
    "ACTOR_REGISTRY",
    "PLATFORM_DEFAULTS",
    "PROFILE_ACTORS",
]


class ApifyAdapter:
    """
    Adapter for fetching social signals via Apify actors.

    Supports three levels of usage:

    1. High-level convenience methods:
       adapter.search_twitter("AI agents")
       adapter.search_linkedin("B2B marketing")

    2. Mid-level with actor selection:
       adapter.fetch_signals("query", actor="apidojo/tweet-scraper")
       adapter.fetch_signals("@username", actor="apidojo/twitter-user-scraper")

    3. Low-level raw execution:
       result = adapter.run_actor("any/actor", {"custom": "input"})
       signals = adapter.parse_results(result, field_mapping=custom_mapping)
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Apify adapter.

        Args:
            config: Configuration dict with api_token and optional settings
        """
        self.api_token = config.get("api_token") or config.get("api_key")
        if not self.api_token:
            raise ValueError("api_token is required for ApifyAdapter")

        # Initialize shared ApifyClient
        try:
            self._client = ApifyClient(api_key=self.api_token)
        except ApifyAuthError as e:
            raise ValueError(f"Invalid API token: {e}")

        self.default_actor = config.get("default_actor", PLATFORM_DEFAULTS["twitter"])

        # Actor registry
        self.actor_registry = {**ACTOR_REGISTRY}

        # Custom field mappings from config
        self._custom_mappings: dict[str, FieldMapping] = {}

    def register_actor(self, actor_config: ActorConfig) -> None:
        """Register a custom actor configuration."""
        self.actor_registry[actor_config.actor_id] = actor_config

    def set_field_mapping(self, actor_id: str, mapping: FieldMapping) -> None:
        """Set custom field mapping for an actor."""
        self._custom_mappings[actor_id] = mapping

    def test_connection(self) -> bool:
        """Test API token validity."""
        return self._client.test_connection()

    def get_user_info(self) -> dict[str, Any] | None:
        """Get user account information."""
        return self._client.get_user_info()

    def list_actors(self) -> list[dict[str, str]]:
        """List all registered actors with descriptions."""
        return [
            {
                "actor_id": cfg.actor_id,
                "source_name": cfg.source_name,
                "description": cfg.description,
            }
            for cfg in self.actor_registry.values()
        ]

    # =========================================================================
    # Low-level API: Raw actor execution
    # =========================================================================

    def run_actor(
        self,
        actor: str,
        actor_input: dict[str, Any],
        timeout: float = 120.0,
    ) -> list[dict[str, Any]]:
        """
        Run an Apify actor with raw input and return raw output.

        Args:
            actor: Actor ID (e.g., "apidojo/tweet-scraper")
            actor_input: Raw input dict passed directly to the actor
            timeout: Request timeout in seconds

        Returns:
            Raw list of result items from the actor

        Raises:
            Exception: If actor run fails
        """
        try:
            return self._client.run_actor(actor, actor_input, timeout=timeout)
        except ApifyError as e:
            raise Exception(str(e))

    def parse_results(
        self,
        items: list[dict[str, Any]],
        source: str = "apify",
        query: str = "",
        field_mapping: FieldMapping | None = None,
    ) -> list[Signal]:
        """
        Parse raw actor results into Signal objects.

        Args:
            items: Raw result items from run_actor()
            source: Source name for signals (e.g., "twitter")
            query: Original query (stored in keywords)
            field_mapping: Custom field mapping (uses defaults if None)

        Returns:
            List of Signal objects
        """
        mapping = field_mapping or FieldMapping()
        signals = []

        for item in items:
            try:
                signal = self._parse_item_with_mapping(item, source, query, mapping)
                if signal:
                    signals.append(signal)
            except Exception:
                continue

        return signals

    # =========================================================================
    # Mid-level API: Actor-aware execution
    # =========================================================================

    def fetch_signals(
        self,
        query: str,
        actor: str | None = None,
        max_items: int = 50,
        keywords: Optional[list[str]] = None,
        actor_input: dict[str, Any] | None = None,
        field_mapping: FieldMapping | None = None,
        **kwargs: Any,
    ) -> list[Signal]:
        """
        Fetch social signals via Apify actor.

        Args:
            query: Search term, hashtag, or profile username
            actor: Apify actor ID (uses default if None)
            max_items: Maximum items to return
            keywords: Optional keyword filter (applied after fetch)
            actor_input: Raw actor input (bypasses input building if provided)
            field_mapping: Custom field mapping for output parsing
            **kwargs: Additional actor-specific parameters

        Returns:
            List of Signal objects sorted by relevance
        """
        actor = actor or self.default_actor

        # Get actor config if registered
        actor_config = self.actor_registry.get(actor)

        # Build or use provided input
        if actor_input is not None:
            final_input = actor_input
        elif actor_config and actor_config.build_input:
            final_input = actor_config.build_input(query, max_items, kwargs)
        else:
            final_input = _build_generic_search_input(query, max_items, kwargs)

        # Run actor
        items = self.run_actor(actor, final_input)

        # Determine source name
        source = actor_config.source_name if actor_config else self._guess_source(actor)

        # Get field mapping (priority: param > custom > actor config > default)
        mapping = (
            field_mapping
            or self._custom_mappings.get(actor)
            or (actor_config.field_mapping if actor_config else None)
            or FieldMapping()
        )

        # Parse results
        signals = self.parse_results(items, source, query, mapping)

        # Filter by keywords if provided
        if keywords:
            signals = [s for s in signals if s.matches_keywords(keywords)]

        # Sort by relevance
        signals.sort(key=lambda s: s.relevance_score, reverse=True)

        return signals[:max_items]

    # =========================================================================
    # High-level API: Platform convenience methods
    # =========================================================================

    def search_twitter(
        self,
        query: str,
        max_items: int = 50,
        keywords: Optional[list[str]] = None,
        actor: str | None = None,
        **kwargs: Any,
    ) -> list[Signal]:
        """
        Search Twitter/X for posts matching query.

        Args:
            query: Search term or hashtag
            max_items: Maximum items to return
            keywords: Optional keyword filter
            actor: Specific Twitter actor (uses default if None)
            **kwargs: Additional actor parameters
        """
        actor = actor or PLATFORM_DEFAULTS["twitter"]
        return self.fetch_signals(
            query=query,
            actor=actor,
            max_items=max_items,
            keywords=keywords,
            **kwargs,
        )

    def search_linkedin(
        self,
        query: str,
        max_items: int = 50,
        keywords: Optional[list[str]] = None,
        actor: str | None = None,
        **kwargs: Any,
    ) -> list[Signal]:
        """
        Search LinkedIn for posts matching query.

        Args:
            query: Search term or LinkedIn search URL
            max_items: Maximum items to return
            keywords: Optional keyword filter
            actor: Specific LinkedIn actor (uses default if None)
            **kwargs: Additional actor parameters
        """
        actor = actor or PLATFORM_DEFAULTS["linkedin"]
        return self.fetch_signals(
            query=query,
            actor=actor,
            max_items=max_items,
            keywords=keywords,
            **kwargs,
        )

    def search_threads(
        self,
        query: str,
        max_items: int = 50,
        keywords: Optional[list[str]] = None,
        actor: str | None = None,
        **kwargs: Any,
    ) -> list[Signal]:
        """
        Search Threads for posts matching query.

        Args:
            query: Search term or hashtag
            max_items: Maximum items to return
            keywords: Optional keyword filter
            actor: Specific Threads actor (uses default if None)
            **kwargs: Additional actor parameters
        """
        actor = actor or PLATFORM_DEFAULTS["threads"]
        return self.fetch_signals(
            query=query,
            actor=actor,
            max_items=max_items,
            keywords=keywords,
            **kwargs,
        )

    def scrape_profile(
        self,
        profile: str,
        platform: str = "twitter",
        max_items: int = 50,
        **kwargs: Any,
    ) -> list[Signal]:
        """
        Scrape posts from a specific profile.

        Args:
            profile: Username or profile URL
            platform: Platform name (twitter, linkedin)
            max_items: Maximum items to return
            **kwargs: Additional actor parameters
        """
        profile_actors = {
            "twitter": "apidojo/twitter-user-scraper",
            "linkedin": "anchor/linkedin-profile-scraper",
        }

        actor = profile_actors.get(platform)
        if not actor:
            raise ValueError(f"No profile scraper available for platform: {platform}")

        return self.fetch_signals(
            query=profile,
            actor=actor,
            max_items=max_items,
            **kwargs,
        )

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _guess_source(self, actor: str) -> str:
        """Guess source name from actor ID."""
        actor_lower = actor.lower()
        if "twitter" in actor_lower or "tweet" in actor_lower:
            return "twitter"
        elif "linkedin" in actor_lower:
            return "linkedin"
        elif "threads" in actor_lower:
            return "threads"
        return "apify"

    def _extract_field(
        self,
        item: dict[str, Any],
        field_spec: str | list[str] | Callable[[dict], Any],
    ) -> Any:
        """Extract a field value using the field specification."""
        if callable(field_spec):
            return field_spec(item)
        elif isinstance(field_spec, list):
            for field_name in field_spec:
                value = self._get_nested(item, field_name)
                if value is not None:
                    return value
            return None
        else:
            return self._get_nested(item, field_spec)

    def _get_nested(self, item: dict[str, Any], field_name: str) -> Any:
        """Get a possibly nested field value (supports dot notation)."""
        if "." in field_name:
            parts = field_name.split(".")
            value = item
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        return item.get(field_name)

    def _parse_item_with_mapping(
        self,
        item: dict[str, Any],
        source: str,
        query: str,
        mapping: FieldMapping,
    ) -> Signal | None:
        """Parse a single item using field mapping."""
        text = self._extract_field(item, mapping.text) or ""
        url = self._extract_field(item, mapping.url) or ""

        if not text and not url:
            return None

        # Extract ID
        item_id = self._extract_field(item, mapping.id)
        if not item_id:
            item_id = hashlib.md5(f"{url}{text[:100]}".encode()).hexdigest()[:12]
        signal_id = f"{source}_{item_id}"

        # Extract metrics
        score = self._extract_field(item, mapping.score) or 0
        comment_count = self._extract_field(item, mapping.comments) or 0

        # Extract author
        author_value = self._extract_field(item, mapping.author)
        if isinstance(author_value, dict):
            author = author_value.get("username") or author_value.get("name")
        else:
            author = author_value

        # Parse timestamp
        timestamp = self._parse_date(self._extract_field(item, mapping.timestamp))

        # Title is first line or truncated text
        title = text.split("\n")[0][:200] if text else url[:200]

        return Signal(
            signal_id=signal_id,
            source=source,
            title=title,
            url=url,
            snippet=text[:500] if text else None,
            timestamp=timestamp,
            author=author,
            score=int(score) if score else 0,
            comment_count=int(comment_count) if comment_count else 0,
            keywords=[query] if query else [],
        )

    def _parse_date(self, date_str: str | None) -> datetime:
        """Parse ISO date string with fallback to now."""
        if not date_str:
            return datetime.now()
        try:
            if isinstance(date_str, str):
                clean = date_str.replace("Z", "+00:00")
                return datetime.fromisoformat(clean)
            return datetime.now()
        except (ValueError, TypeError):
            return datetime.now()
