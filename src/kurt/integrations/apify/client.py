"""
Apify API client.

Provides low-level and mid-level API access to Apify actors.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from kurt.integrations.apify.parsers import FieldMapping, ParsedItem, parse_items
from kurt.integrations.apify.registry import (
    ACTOR_REGISTRY,
    PLATFORM_DEFAULTS,
    PROFILE_ACTORS,
    ActorConfig,
    get_actor_config,
    guess_source_from_actor,
)


class ApifyError(Exception):
    """Base exception for Apify errors."""

    pass


class ApifyAuthError(ApifyError):
    """Authentication error (invalid API key)."""

    pass


class ApifyTimeoutError(ApifyError):
    """Actor execution timeout."""

    pass


class ApifyActorError(ApifyError):
    """Actor execution failed."""

    pass


class ApifyClient:
    """
    Low-level Apify API client.

    Handles HTTP communication with Apify API, including:
    - Actor execution (sync and async)
    - Dataset retrieval
    - Error handling and retries

    Usage:
        client = ApifyClient(api_key="...")
        items = client.run_actor("apidojo/tweet-scraper", {"searchTerms": ["AI"]})
    """

    BASE_URL = "https://api.apify.com/v2"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 2,
    ):
        """
        Initialize Apify client.

        Args:
            api_key: Apify API token. If not provided, reads from APIFY_API_KEY env var.
            timeout: Default request timeout in seconds
            max_retries: Number of retries for transient failures
        """
        self.api_key = api_key or os.environ.get("APIFY_API_KEY")
        if not self.api_key:
            raise ApifyAuthError(
                "Apify API key required. Set APIFY_API_KEY env var or pass api_key parameter."
            )

        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialized httpx client."""
        if self._client is None:
            self._client = httpx.Client(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ApifyClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # =========================================================================
    # Connection & Account
    # =========================================================================

    def test_connection(self) -> bool:
        """Test API key validity."""
        try:
            response = self.client.get(f"{self.BASE_URL}/users/me")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def get_user_info(self) -> dict[str, Any] | None:
        """Get user account information."""
        try:
            response = self.client.get(f"{self.BASE_URL}/users/me")
            if response.status_code == 200:
                return response.json()
            return None
        except httpx.RequestError:
            return None

    # =========================================================================
    # Low-level: Raw Actor Execution
    # =========================================================================

    def run_actor(
        self,
        actor_id: str,
        actor_input: dict[str, Any],
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run an Apify actor synchronously and return raw results.

        This is the lowest-level method - it passes input directly to the actor
        and returns raw output without any parsing.

        Args:
            actor_id: Actor ID (e.g., "apidojo/tweet-scraper")
            actor_input: Raw input dict passed directly to the actor
            timeout: Request timeout (uses default if None)

        Returns:
            Raw list of result items from the actor

        Raises:
            ApifyAuthError: Invalid API key
            ApifyTimeoutError: Actor execution timed out
            ApifyActorError: Actor execution failed
            ApifyError: Other API errors
        """
        timeout = timeout or self.timeout

        try:
            response = self.client.post(
                f"{self.BASE_URL}/acts/{actor_id}/run-sync-get-dataset-items",
                json=actor_input,
                timeout=timeout,
            )

            if response.status_code == 401:
                raise ApifyAuthError("Invalid Apify API key")
            elif response.status_code == 404:
                raise ApifyActorError(f"Actor not found: {actor_id}")

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise ApifyTimeoutError(
                f"Apify actor {actor_id} timed out after {timeout} seconds"
            )
        except httpx.HTTPStatusError as e:
            raise ApifyActorError(
                f"Apify API error: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ApifyError(f"Failed to connect to Apify: {e}")

    def run_actor_async(
        self,
        actor_id: str,
        actor_input: dict[str, Any],
    ) -> str:
        """
        Start an actor run asynchronously.

        Args:
            actor_id: Actor ID
            actor_input: Raw input dict

        Returns:
            Run ID for polling status

        Raises:
            ApifyError: If actor start fails
        """
        try:
            response = self.client.post(
                f"{self.BASE_URL}/acts/{actor_id}/runs",
                json=actor_input,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]["id"]
        except httpx.HTTPStatusError as e:
            raise ApifyActorError(
                f"Failed to start actor: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise ApifyError(f"Failed to connect to Apify: {e}")

    def get_run_status(self, run_id: str) -> dict[str, Any]:
        """
        Get status of an async actor run.

        Args:
            run_id: Run ID from run_actor_async

        Returns:
            Run status dict with 'status', 'finishedAt', etc.
        """
        response = self.client.get(f"{self.BASE_URL}/actor-runs/{run_id}")
        response.raise_for_status()
        return response.json()["data"]

    def get_dataset_items(
        self,
        dataset_id: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get items from a dataset.

        Args:
            dataset_id: Dataset ID
            limit: Maximum items to return
            offset: Starting offset

        Returns:
            List of dataset items
        """
        params: dict[str, Any] = {"offset": offset}
        if limit:
            params["limit"] = limit

        response = self.client.get(
            f"{self.BASE_URL}/datasets/{dataset_id}/items",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Mid-level: Actor-aware Execution
    # =========================================================================

    def fetch(
        self,
        query: str,
        actor_id: str | None = None,
        platform: str | None = None,
        max_items: int = 50,
        field_mapping: FieldMapping | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> list[ParsedItem]:
        """
        Fetch and parse results from an Apify actor.

        This mid-level method handles:
        - Actor selection from platform or actor_id
        - Input building using registered actor config
        - Output parsing with field mapping

        Args:
            query: Search term, URL, or platform-specific identifier
            actor_id: Specific actor ID (takes precedence over platform)
            platform: Platform name (twitter, linkedin, etc.) to use default actor
            max_items: Maximum items to return
            field_mapping: Custom field mapping for parsing
            timeout: Request timeout
            **kwargs: Additional actor-specific parameters

        Returns:
            List of ParsedItem objects

        Raises:
            ValueError: If neither actor_id nor platform specified
            ApifyError: If actor execution fails
        """
        # Determine actor to use
        if actor_id:
            pass
        elif platform:
            actor_id = PLATFORM_DEFAULTS.get(platform.lower())
            if not actor_id:
                raise ValueError(f"Unknown platform: {platform}")
        else:
            raise ValueError("Must specify either actor_id or platform")

        # Get actor config if registered
        actor_config = get_actor_config(actor_id)

        # Build input
        if actor_config and actor_config.build_input:
            actor_input = actor_config.build_input(query, max_items, kwargs)
        else:
            # Generic fallback
            actor_input = {
                "searchTerms": [query],
                "maxItems": max_items,
                **kwargs,
            }

        # Run actor
        items = self.run_actor(actor_id, actor_input, timeout=timeout)

        # Determine source and mapping
        source = actor_config.source_name if actor_config else guess_source_from_actor(actor_id)
        mapping = (
            field_mapping
            or (actor_config.field_mapping if actor_config else None)
            or FieldMapping()
        )

        # Parse results
        return parse_items(items, source, mapping)

    def fetch_profile(
        self,
        profile: str,
        platform: str,
        max_items: int = 50,
        **kwargs: Any,
    ) -> list[ParsedItem]:
        """
        Fetch posts from a specific profile.

        Args:
            profile: Username or profile URL
            platform: Platform name (twitter, linkedin, substack)
            max_items: Maximum items to return
            **kwargs: Additional actor parameters

        Returns:
            List of ParsedItem objects

        Raises:
            ValueError: If no profile scraper available for platform
        """
        actor_id = PROFILE_ACTORS.get(platform.lower())
        if not actor_id:
            raise ValueError(f"No profile scraper available for platform: {platform}")

        return self.fetch(
            query=profile,
            actor_id=actor_id,
            max_items=max_items,
            **kwargs,
        )

    # =========================================================================
    # High-level: Platform Convenience Methods
    # =========================================================================

    def search_twitter(
        self,
        query: str,
        max_items: int = 50,
        **kwargs: Any,
    ) -> list[ParsedItem]:
        """Search Twitter/X for posts matching query."""
        return self.fetch(query=query, platform="twitter", max_items=max_items, **kwargs)

    def search_linkedin(
        self,
        query: str,
        max_items: int = 50,
        **kwargs: Any,
    ) -> list[ParsedItem]:
        """Search LinkedIn for posts matching query."""
        return self.fetch(query=query, platform="linkedin", max_items=max_items, **kwargs)

    def search_threads(
        self,
        query: str,
        max_items: int = 50,
        **kwargs: Any,
    ) -> list[ParsedItem]:
        """Search Threads for posts matching query."""
        return self.fetch(query=query, platform="threads", max_items=max_items, **kwargs)

    def search_substack(
        self,
        query: str,
        max_items: int = 50,
        **kwargs: Any,
    ) -> list[ParsedItem]:
        """Search/scrape Substack newsletters."""
        return self.fetch(query=query, platform="substack", max_items=max_items, **kwargs)


# Convenience function for one-off usage
def run_actor(
    actor_id: str,
    actor_input: dict[str, Any],
    api_key: str | None = None,
    timeout: float = 120.0,
) -> list[dict[str, Any]]:
    """
    Run an Apify actor and return raw results.

    Convenience function that creates a client, runs the actor, and cleans up.

    Args:
        actor_id: Actor ID (e.g., "apidojo/tweet-scraper")
        actor_input: Raw input dict
        api_key: Apify API token (uses env var if not provided)
        timeout: Request timeout

    Returns:
        Raw list of result items
    """
    with ApifyClient(api_key=api_key, timeout=timeout) as client:
        return client.run_actor(actor_id, actor_input)
